from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, model_validator


ScheduleRuleType = Literal["daily", "weekly", "monthly"]


class TaskScheduleCreate(BaseModel):
    rule_type: ScheduleRuleType
    interval: int = Field(default=1, ge=1, le=365)
    weekdays: Optional[List[int]] = None
    day_of_month: Optional[int] = Field(default=None, ge=1, le=31)
    starts_on: Optional[date] = None
    ends_on: Optional[date] = None
    timezone: str = "Asia/Shanghai"
    is_active: bool = True

    @model_validator(mode="after")
    def validate_rule(self):
        if self.rule_type == "weekly":
            if not self.weekdays:
                raise ValueError("weekly schedules require at least one weekday")
            if len(set(self.weekdays)) != len(self.weekdays):
                raise ValueError("weekdays must not contain duplicates")
            if any(day < 0 or day > 6 for day in self.weekdays):
                raise ValueError("weekdays must use values from 0 to 6")
        elif self.weekdays:
            raise ValueError("weekdays are only valid for weekly schedules")

        if self.rule_type == "monthly" and self.day_of_month is not None:
            if not 1 <= self.day_of_month <= 31:
                raise ValueError("day_of_month must use values from 1 to 31")
        elif self.rule_type != "monthly" and self.day_of_month is not None:
            raise ValueError("day_of_month is only valid for monthly schedules")

        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")

        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return self


class TaskScheduleResponse(BaseModel):
    id: UUID
    task_id: UUID
    rule_type: ScheduleRuleType
    interval: int
    weekdays: List[int] = Field(default_factory=list)
    day_of_month: Optional[int] = None
    starts_on: date
    ends_on: Optional[date] = None
    timezone: str
    is_active: bool

    model_config = {"from_attributes": True}


class TaskOccurrenceResponse(BaseModel):
    id: UUID
    task_id: UUID
    occurrence_date: date
    status: str
    snoozed_until: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    source_key: str

    model_config = {"from_attributes": True}


class TaskScheduleStateResponse(BaseModel):
    task_id: UUID
    title: str
    occurrence_date: date
    status: str
    deadline: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    schedule: Optional[TaskScheduleResponse] = None


class TaskSnoozeRequest(BaseModel):
    until: datetime
    occurrence_date: Optional[date] = None


class TaskRescheduleRequest(BaseModel):
    deadline: Optional[datetime] = None
    occurrence_date: Optional[date] = None
    new_occurrence_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.deadline is None and self.new_occurrence_date is None:
            raise ValueError("provide deadline or new_occurrence_date")
        if self.deadline is not None and self.new_occurrence_date is not None:
            raise ValueError("deadline and new_occurrence_date cannot be combined")
        if self.new_occurrence_date is not None and self.occurrence_date is None:
            raise ValueError("occurrence_date is required when moving an occurrence")
        return self
