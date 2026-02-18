from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Global Settings ---



class GlobalSettingsUpdate(BaseModel):
    horizon_days: int | None = Field(default=None, ge=1, description="How far ahead clients can book (days)")
    min_notice_hours: int | None = Field(default=None, ge=0, description="Minimum notice before first slot (hours)")
    hard_cutoff_date: str | None = Field(default=None, description="Last bookable date (ISO-8601)")


class GlobalSettingsResponse(BaseModel):
    horizon_days: int
    min_notice_hours: int
    hard_cutoff_date: str | None
    created_at: str
    updated_at: str


# --- Monthly Recurring Rules ---

class RuleCreate(BaseModel):
    day_of_month: int = Field(ge=1, le=31, description="Day of month (1-31)")
    available_slots: list[str] = Field(description="List of times in HH:MM format (UTC)")


class RuleUpdate(BaseModel):
    available_slots: list[str] = Field(description="List of times in HH:MM format (UTC)")


class RuleResponse(BaseModel):
    day_of_month: int
    available_slots: list[str]
    created_at: str
    updated_at: str


# --- Date Overrides ---

OverrideType = Literal["BLOCKED", "MODIFIED"]


class DateOverrideCreate(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD format")
    type: OverrideType = Field(description="BLOCKED = no availability; MODIFIED = use overrideSlots")
    override_slots: list[str] = Field(default_factory=list, description="For MODIFIED: list of times (UTC)")


class DateOverrideUpdate(BaseModel):
    type: OverrideType | None = None
    override_slots: list[str] | None = None


class DateOverrideResponse(BaseModel):
    date: str
    type: OverrideType
    override_slots: list[str]
    created_at: str
    updated_at: str


# --- Appointments ---

BookingStatus = Literal["PENDING", "CONFIRMED", "CANCELLED"]


class AppointmentCreate(BaseModel):
    date: str = Field(description="Date in YYYY-MM-DD")
    time: str = Field(description="Time in HHMM format (e.g. 0930)")
    client_mobile: str = Field(description="Client mobile number (unique identifier)")
    appointment_details: dict[str, Any] = Field(default_factory=dict)
    status: BookingStatus = "PENDING"


class AppointmentUpdate(BaseModel):
    date: str | None = Field(default=None, description="New date for reschedule")
    time: str | None = Field(default=None, description="New time for reschedule")
    appointment_details: dict[str, Any] | None = None
    status: BookingStatus | None = None


class AppointmentResponse(BaseModel):
    date: str
    time: str
    sk: str
    client_mobile: str
    status: BookingStatus
    appointment_details: dict[str, Any]
    created_at: str
    updated_at: str


# --- Availability ---

class AvailabilityQuery(BaseModel):
    start_date: str = Field(description="Start date YYYY-MM-DD")
    end_date: str = Field(description="End date YYYY-MM-DD")


class DayAvailability(BaseModel):
    date: str
    slots: list[str]


class AvailabilityResponse(BaseModel):
    available: list[DayAvailability]
