from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.calendar.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    AvailabilityResponse,
    DateOverrideCreate,
    DateOverrideResponse,
    DateOverrideUpdate,
    DayAvailability,
    GlobalSettingsResponse,
    GlobalSettingsUpdate,
    RuleCreate,
    RuleResponse,
    RuleUpdate,
)
from app.calendar.service import CalendarService, ConflictError
from app.users.models import User

router = APIRouter()


def _settings_to_response(item: dict) -> GlobalSettingsResponse:
    return GlobalSettingsResponse(
        horizon_days=item["horizonDays"],
        min_notice_hours=item["minNoticeHours"],
        hard_cutoff_date=item.get("hardCutoffDate"),
        created_at=item["createdAt"],
        updated_at=item["updatedAt"],
    )


def _rule_to_response(item: dict) -> RuleResponse:
    return RuleResponse(
        day_of_month=item["dayOfMonth"],
        available_slots=item["availableSlots"],
        created_at=item["createdAt"],
        updated_at=item["updatedAt"],
    )


def _override_to_response(item: dict) -> DateOverrideResponse:
    return DateOverrideResponse(
        date=item["date"],
        type=item["type"],
        override_slots=item.get("overrideSlots", []),
        created_at=item["createdAt"],
        updated_at=item["updatedAt"],
    )


def _booking_to_response(item: dict) -> AppointmentResponse:
    sk = item["SK"]
    date = sk.replace("BOOKING#", "").split("#")[0]
    time_part = sk.split("T")[1] if "T" in sk else "0000"
    time_str = f"{time_part[:2]}:{time_part[2:]}" if len(time_part) == 4 else time_part
    return AppointmentResponse(
        date=date,
        time=time_str,
        sk=sk,
        client_mobile=item["clientMobile"],
        status=item["status"],
        appointment_details=item.get("appointmentDetails", {}),
        created_at=item["createdAt"],
        updated_at=item["updatedAt"],
    )


# --- Settings ---

@router.get("/settings", response_model=GlobalSettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get or create global calendar settings for the current user."""
    svc = CalendarService()
    item = svc.get_or_create_settings(current_user.id)
    return _settings_to_response(item)


@router.patch("/settings", response_model=GlobalSettingsResponse)
async def update_settings(
    body: GlobalSettingsUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update global calendar settings."""
    svc = CalendarService()
    item = svc.update_settings(
        current_user.id,
        horizon_days=body.horizon_days,
        min_notice_hours=body.min_notice_hours,
        hard_cutoff_date=body.hard_cutoff_date,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Settings not found")
    return _settings_to_response(item)


# --- Monthly Rules ---

@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(current_user: User = Depends(get_current_user)):
    """List all monthly recurring availability rules."""
    svc = CalendarService()
    items = svc.repo.list_rules(current_user.id)
    return [_rule_to_response(r) for r in items]


@router.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    body: RuleCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a monthly recurring rule for a given day of month."""
    svc = CalendarService()
    item = svc.repo.put_rule(
        current_user.id,
        body.day_of_month,
        body.available_slots,
    )
    return _rule_to_response(item)


@router.get("/rules/{day_of_month}", response_model=RuleResponse)
async def get_rule(
    day_of_month: int,
    current_user: User = Depends(get_current_user),
):
    """Get a rule by day of month (1-31)."""
    svc = CalendarService()
    item = svc.repo.get_rule(current_user.id, day_of_month)
    if not item:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_response(item)


@router.patch("/rules/{day_of_month}", response_model=RuleResponse)
async def update_rule(
    day_of_month: int,
    body: RuleUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update available slots for a rule."""
    svc = CalendarService()
    item = svc.repo.get_rule(current_user.id, day_of_month)
    if not item:
        raise HTTPException(status_code=404, detail="Rule not found")
    svc.repo.put_rule(current_user.id, day_of_month, body.available_slots)
    return _rule_to_response(svc.repo.get_rule(current_user.id, day_of_month))


@router.delete("/rules/{day_of_month}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    day_of_month: int,
    current_user: User = Depends(get_current_user),
):
    """Delete a monthly rule."""
    svc = CalendarService()
    svc.repo.delete_rule(current_user.id, day_of_month)


# --- Date Overrides ---

@router.get("/overrides/{date}", response_model=DateOverrideResponse)
async def get_override(
    date: str,
    current_user: User = Depends(get_current_user),
):
    """Get date-specific override for a given date."""
    svc = CalendarService()
    item = svc.repo.get_date_override(current_user.id, date)
    if not item:
        raise HTTPException(status_code=404, detail="Override not found")
    return _override_to_response(item)


@router.put("/overrides/{date}", response_model=DateOverrideResponse)
async def upsert_override(
    date: str,
    body: DateOverrideCreate,
    current_user: User = Depends(get_current_user),
):
    """Create or replace a date override (body.date must match path)."""
    if body.date != date:
        raise HTTPException(status_code=400, detail="Date in path must match body")
    svc = CalendarService()
    item = svc.repo.put_date_override(
        current_user.id,
        date,
        body.type,
        body.override_slots,
    )
    return _override_to_response(item)


@router.delete("/overrides/{date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    date: str,
    current_user: User = Depends(get_current_user),
):
    """Remove a date override."""
    svc = CalendarService()
    svc.repo.delete_date_override(current_user.id, date)


# --- Availability ---

@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
):
    """Get available slots for a date range (minus overrides and bookings)."""
    svc = CalendarService()
    days = svc.get_availability(current_user.id, start_date, end_date)
    return AvailabilityResponse(
        available=[DayAvailability(date=d["date"], slots=d["slots"]) for d in days],
    )


# --- Appointments ---

@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    body: AppointmentCreate,
    current_user: User = Depends(get_current_user),
):
    """Book an appointment. Returns 409 if slot is already taken."""
    svc = CalendarService()
    try:
        item = svc.create_booking(
            user_id=current_user.id,
            date=body.date,
            time_hhmm=body.time,
            client_mobile=body.client_mobile,
            appointment_details=body.appointment_details,
            status=body.status,
        )
    except ConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot already booked",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _booking_to_response(item)


@router.get("/appointments/{date}/{time}", response_model=AppointmentResponse)
async def get_appointment(
    date: str,
    time: str,
    current_user: User = Depends(get_current_user),
):
    """Get an appointment by date and time (time as HHMM or HH:MM)."""
    svc = CalendarService()
    item = svc.get_booking(current_user.id, date, time)
    if not item:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _booking_to_response(item)


@router.patch("/appointments/{date}/{time}", response_model=AppointmentResponse)
async def update_appointment(
    date: str,
    time: str,
    body: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update or reschedule an appointment."""
    svc = CalendarService()
    if body.date is not None and body.time is not None:
        try:
            item = svc.reschedule_booking(
                user_id=current_user.id,
                old_date=date,
                old_time=time,
                new_date=body.date,
                new_time=body.time,
            )
            return _booking_to_response(item)
        except ConflictError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New slot already booked",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    item = svc.get_booking(current_user.id, date, time)
    if not item:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if body.status is not None:
        if body.status == "CANCELLED":
            item = svc.cancel_booking(current_user.id, date, time)
        else:
            item = svc.update_booking(
                current_user.id, date, time, status=body.status
            )
    if body.appointment_details is not None and item:
        item = svc.update_booking(
            current_user.id, date, time, appointment_details=body.appointment_details
        )
    return _booking_to_response(item)


@router.delete("/appointments/{date}/{time}")
async def cancel_appointment(
    date: str,
    time: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel an appointment (soft delete: status → CANCELLED)."""
    svc = CalendarService()
    item = svc.cancel_booking(current_user.id, date, time)
    if not item:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return _booking_to_response(item)
