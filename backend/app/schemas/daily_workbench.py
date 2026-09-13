from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class DailyFocusUpdate(BaseModel):
    date: date
    revision: int = Field(ge=0)
    task_ids: list[UUID] = Field(max_length=3)

    @field_validator("task_ids")
    @classmethod
    def unique_tasks(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("重点任务不能重复")
        return value


class QuickTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    schedule: Literal["today", "unscheduled", "date"] = "today"
    due_date: date | None = None
    request_id: UUID

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.schedule == "date" and self.due_date is None:
            raise ValueError("请选择截止日期")
        if self.schedule != "date" and self.due_date is not None:
            raise ValueError("只有指定日期的任务可以填写截止日期")
        return self
