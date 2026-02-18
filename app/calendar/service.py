from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from app.calendar.repository import CalendarRepository


class ConflictError(Exception):
    """Raised when a booking slot is already taken."""

    pass


def _parse_slot(s: str) -> str:
    """Normalize slot to HH:MM (e.g. '0930' -> '09:30', '09:30' -> '09:30')."""
    s = s.replace(":", "").strip()
    if len(s) == 4:
        return f"{s[:2]}:{s[2:]}"
    return s


def _slot_to_hhmm(s: str) -> str:
    """Convert HH:MM to HHMM for SK."""
    return s.replace(":", "")


def _date_from_iso(d: str) -> datetime:
    return datetime.fromisoformat(d.replace("Z", "+00:00"))


def _iterate_dates(start: str, end: str):
    s = _date_from_iso(start + "T00:00:00Z")
    e = _date_from_iso(end + "T00:00:00Z")
    while s <= e:
        yield s.strftime("%Y-%m-%d")
        s += timedelta(days=1)


class CalendarService:
    def __init__(self) -> None:
        self.repo = CalendarRepository()

    def get_or_create_settings(self, user_id: str) -> dict:
        s = self.repo.get_settings(user_id)
        if s:
            return s
        self.repo.put_settings(
            user_id=user_id,
            horizon_days=30,
            min_notice_hours=2,
        )
        return self.repo.get_settings(user_id)

    def update_settings(
        self,
        user_id: str,
        *,
        horizon_days: int | None = None,
        min_notice_hours: int | None = None,
        hard_cutoff_date: str | None = None,
    ) -> dict | None:
        return self.repo.update_settings(
            user_id,
            horizon_days=horizon_days,
            min_notice_hours=min_notice_hours,
            hard_cutoff_date=hard_cutoff_date,
        )

    def get_availability(self, user_id: str, start_date: str, end_date: str) -> list[dict]:
        settings = self.get_or_create_settings(user_id)
        rules = {
            int(r["dayOfMonth"]): r["availableSlots"]
            for r in self.repo.list_rules(user_id)
        }
        overrides = {
            o["date"]: o
            for o in self.repo.list_date_overrides(user_id, start_date, end_date)
        }
        bookings = self.repo.list_bookings_for_range(user_id, start_date, end_date)
        booked = {}
        for b in bookings:
            if b.get("status") in ("PENDING", "CONFIRMED"):
                date = b["SK"].replace("BOOKING#", "").split("#")[0]
                time_str = b["SK"].split("T")[1] if "T" in b["SK"] else ""
                if len(time_str) == 4:
                    time_str = f"{time_str[:2]}:{time_str[2:]}"
                booked.setdefault(date, set()).add(time_str)

        min_notice = int(settings.get("minNoticeHours", 0) or 0)
        horizon = int(settings.get("horizonDays", 30) or 30)
        hard_cutoff = settings.get("hardCutoffDate")
        now = datetime.now(timezone.utc)

        result = []
        for d in _iterate_dates(start_date, end_date):
            if hard_cutoff and d > hard_cutoff:
                continue

            override = overrides.get(d)
            if override:
                if override["type"] == "BLOCKED":
                    continue
                base_slots = [
                    _parse_slot(s) for s in override.get("overrideSlots", [])
                ]
            else:
                day_num = _date_from_iso(d + "T00:00:00Z").day
                base_slots = [
                    _parse_slot(s)
                    for s in rules.get(day_num, [])
                ]

            taken = booked.get(d, set())
            available = [
                s for s in base_slots
                if _parse_slot(s) not in taken
            ]

            # Apply min notice
            if min_notice > 0:
                cutoff = now + timedelta(hours=min_notice)
                available = [
                    s for s in available
                    if _date_from_iso(d + f"T{s}:00Z") >= cutoff
                ]

            if available:
                result.append({"date": d, "slots": sorted(available)})

        return result

    def create_booking(
        self,
        user_id: str,
        date: str,
        time_hhmm: str,
        client_mobile: str,
        appointment_details: dict | None = None,
        status: str = "PENDING",
    ) -> dict:
        time_hhmm = time_hhmm.replace(":", "")
        if len(time_hhmm) != 4:
            raise ValueError("time must be HHMM (e.g. 0930)")
        try:
            self.repo.put_booking(
                user_id=user_id,
                date=date,
                time_hhmm=time_hhmm,
                client_mobile=client_mobile,
                status=status,
                appointment_details=appointment_details or {},
                condition="not_exists",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ConflictError("Slot already booked") from e
            raise
        return self.repo.get_booking(user_id, date, time_hhmm)

    def reschedule_booking(
        self,
        user_id: str,
        old_date: str,
        old_time: str,
        new_date: str,
        new_time: str,
    ) -> dict:
        old_time = old_time.replace(":", "")
        new_time = new_time.replace(":", "")
        old_item = self.repo.get_booking(user_id, old_date, old_time)
        if not old_item or old_item.get("status") == "CANCELLED":
            raise ValueError("Booking not found or already cancelled")
        created_at = old_item.get("createdAt")
        client_mobile = old_item["clientMobile"]
        details = old_item.get("appointmentDetails", {})
        self.repo.delete_booking(user_id, old_date, old_time)
        try:
            self.repo.put_booking(
                user_id=user_id,
                date=new_date,
                time_hhmm=new_time,
                client_mobile=client_mobile,
                status=old_item.get("status", "PENDING"),
                appointment_details=details,
                created_at=created_at,
                condition="not_exists",
            )
        except ClientError as e:
            self.repo.put_booking(
                user_id=user_id,
                date=old_date,
                time_hhmm=old_time,
                client_mobile=client_mobile,
                status=old_item.get("status", "PENDING"),
                appointment_details=details,
                created_at=created_at,
            )
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ConflictError("New slot already booked") from e
            raise
        return self.repo.get_booking(user_id, new_date, new_time)

    def cancel_booking(self, user_id: str, date: str, time_hhmm: str) -> dict | None:
        time_hhmm = time_hhmm.replace(":", "")
        item = self.repo.get_booking(user_id, date, time_hhmm)
        if not item:
            return None
        now = datetime.now(timezone.utc).isoformat()
        item["status"] = "CANCELLED"
        item["updatedAt"] = now
        self.repo.put_booking_unconditional(item)
        return item

    def get_booking(self, user_id: str, date: str, time_hhmm: str) -> dict | None:
        time_hhmm = time_hhmm.replace(":", "")
        return self.repo.get_booking(user_id, date, time_hhmm)

    def update_booking(
        self,
        user_id: str,
        date: str,
        time_hhmm: str,
        *,
        status: str | None = None,
        appointment_details: dict | None = None,
    ) -> dict | None:
        time_hhmm = time_hhmm.replace(":", "")
        item = self.repo.get_booking(user_id, date, time_hhmm)
        if not item:
            return None
        if status is not None:
            item["status"] = status
        if appointment_details is not None:
            item["appointmentDetails"] = appointment_details
        item["updatedAt"] = datetime.now(timezone.utc).isoformat()
        self.repo.put_booking_unconditional(item)
        return item
