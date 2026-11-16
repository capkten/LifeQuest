from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.cultivation_retreat import RetreatStartRequest


class CaveStartRequest(RetreatStartRequest):
    request_id: UUID
    mark_todo_complete: bool = True


class CaveAcknowledgeRequest(BaseModel):
    request_id: UUID


class CaveOnboardingCompleteRequest(CaveAcknowledgeRequest):
    session_id: UUID


class CaveSettleRequest(BaseModel):
    request_id: UUID
    early: bool = False


class CaveSignRequest(BaseModel):
    date: date
    request_id: UUID


class CaveSelectRequest(CaveSignRequest):
    task_id: UUID


class CaveOpenEvent(BaseModel):
    request_id: UUID
    event: Literal['cave_open', 'return_view', 'notification_click']
    session_id: UUID | None = None
    notification_type: Literal['ongoing', 'completion', 'finish'] | None = None
    delay_ms: int | None = Field(default=None, strict=True, ge=0, le=9007199254740991,
                                 description='Client-reported notification click delay; telemetry only, not server-measured latency or reward eligibility.')
    source: str = Field(default='direct', min_length=1, max_length=40)
    mode: Literal['morning', 'day', 'dusk', 'night']
    has_active_session: bool

    @model_validator(mode='after')
    def return_requires_session(self):
        if self.event == 'return_view' and self.session_id is None:
            raise ValueError('Return views require a session ID')
        if self.event == 'notification_click' and (self.session_id is None or self.notification_type is None or self.delay_ms is None):
            raise ValueError('Notification clicks require a session ID, notification type and delay')
        return self
