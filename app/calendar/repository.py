from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.database import get_calendar_table


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CalendarRepository:
    """DynamoDB access for calendar table (PK/SK single-table design)."""

    def __init__(self) -> None:
        self.table = get_calendar_table()

    def _pk(self, user_id: str) -> str:
        return f"USER#{user_id}"

    # --- Settings ---

    def get_settings(self, user_id: str) -> dict | None:
        pk = self._pk(user_id)
        sk = "SETTINGS#GLOBAL"
        resp = self.table.get_item(Key={"PK": pk, "SK": sk})
        return resp.get("Item")

    def put_settings(
        self,
        user_id: str,
        horizon_days: int,
        min_notice_hours: int,
        hard_cutoff_date: str | None = None,
    ) -> dict:
        pk = self._pk(user_id)
        sk = "SETTINGS#GLOBAL"
        now = _now()
        item = {
            "PK": pk,
            "SK": sk,
            "horizonDays": horizon_days,
            "minNoticeHours": min_notice_hours,
            "createdAt": now,
            "updatedAt": now,
        }
        if hard_cutoff_date is not None:
            item["hardCutoffDate"] = hard_cutoff_date
        self.table.put_item(Item=item)
        return item

    def update_settings(
        self,
        user_id: str,
        *,
        horizon_days: int | None = None,
        min_notice_hours: int | None = None,
        hard_cutoff_date: str | None = None,
    ) -> dict | None:
        existing = self.get_settings(user_id)
        if not existing:
            return None
        if horizon_days is not None:
            existing["horizonDays"] = horizon_days
        if min_notice_hours is not None:
            existing["minNoticeHours"] = min_notice_hours
        if hard_cutoff_date is not None:
            existing["hardCutoffDate"] = hard_cutoff_date
        existing["updatedAt"] = _now()
        self.table.put_item(Item=existing)
        return existing

    # --- Rules ---

    def get_rule(self, user_id: str, day_of_month: int) -> dict | None:
        pk = self._pk(user_id)
        sk = f"RULE#DOM#{day_of_month:02d}"
        resp = self.table.get_item(Key={"PK": pk, "SK": sk})
        return resp.get("Item")

    def put_rule(self, user_id: str, day_of_month: int, available_slots: list[str]) -> dict:
        pk = self._pk(user_id)
        sk = f"RULE#DOM#{day_of_month:02d}"
        now = _now()
        item = {
            "PK": pk,
            "SK": sk,
            "dayOfMonth": day_of_month,
            "availableSlots": available_slots,
            "createdAt": now,
            "updatedAt": now,
        }
        self.table.put_item(Item=item)
        return item

    def list_rules(self, user_id: str) -> list[dict]:
        pk = self._pk(user_id)
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("RULE#DOM#"),
        )
        return resp.get("Items", [])

    def delete_rule(self, user_id: str, day_of_month: int) -> None:
        pk = self._pk(user_id)
        sk = f"RULE#DOM#{day_of_month:02d}"
        self.table.delete_item(Key={"PK": pk, "SK": sk})

    # --- Date Overrides ---

    def get_date_override(self, user_id: str, date: str) -> dict | None:
        pk = self._pk(user_id)
        sk = f"DATE#{date}"
        resp = self.table.get_item(Key={"PK": pk, "SK": sk})
        return resp.get("Item")

    def put_date_override(
        self,
        user_id: str,
        date: str,
        type: str,
        override_slots: list[str],
    ) -> dict:
        pk = self._pk(user_id)
        sk = f"DATE#{date}"
        now = _now()
        item = {
            "PK": pk,
            "SK": sk,
            "date": date,
            "type": type,
            "overrideSlots": override_slots,
            "createdAt": now,
            "updatedAt": now,
        }
        self.table.put_item(Item=item)
        return item

    def list_date_overrides(self, user_id: str, start_date: str, end_date: str) -> list[dict]:
        pk = self._pk(user_id)
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").between(
                f"DATE#{start_date}",
                f"DATE#{end_date}",
            ),
        )
        return resp.get("Items", [])

    def delete_date_override(self, user_id: str, date: str) -> None:
        pk = self._pk(user_id)
        sk = f"DATE#{date}"
        self.table.delete_item(Key={"PK": pk, "SK": sk})

    # --- Bookings ---

    def get_booking(self, user_id: str, date: str, time_hhmm: str) -> dict | None:
        pk = self._pk(user_id)
        sk = f"BOOKING#{date}#T{time_hhmm}"
        resp = self.table.get_item(Key={"PK": pk, "SK": sk})
        return resp.get("Item")

    def put_booking(
        self,
        user_id: str,
        date: str,
        time_hhmm: str,
        client_mobile: str,
        status: str,
        appointment_details: dict,
        *,
        created_at: str | None = None,
        condition: str | None = None,
    ) -> dict:
        pk = self._pk(user_id)
        sk = f"BOOKING#{date}#T{time_hhmm}"
        now = _now()
        item = {
            "PK": pk,
            "SK": sk,
            "clientMobile": client_mobile,
            "status": status,
            "appointmentDetails": appointment_details,
            "createdAt": created_at or now,
            "updatedAt": now,
        }
        extra = {}
        if condition == "not_exists":
            extra["ConditionExpression"] = "attribute_not_exists(PK)"
        self.table.put_item(Item=item, **extra)
        return item

    def put_booking_unconditional(self, item: dict) -> None:
        self.table.put_item(Item=item)

    def delete_booking(self, user_id: str, date: str, time_hhmm: str) -> None:
        pk = self._pk(user_id)
        sk = f"BOOKING#{date}#T{time_hhmm}"
        self.table.delete_item(Key={"PK": pk, "SK": sk})

    def list_bookings_for_date(self, user_id: str, date: str) -> list[dict]:
        pk = self._pk(user_id)
        sk_prefix = f"BOOKING#{date}#"
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with(sk_prefix),
        )
        return resp.get("Items", [])

    def list_bookings_for_range(self, user_id: str, start_date: str, end_date: str) -> list[dict]:
        pk = self._pk(user_id)
        resp = self.table.query(
            KeyConditionExpression=Key("PK").eq(pk) & Key("SK").between(
                f"BOOKING#{start_date}#T0000",
                f"BOOKING#{end_date}#T2359",
            ),
        )
        return resp.get("Items", [])
