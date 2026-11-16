from uuid import uuid4

from fastapi import HTTPException

from app.models.cave import CaveEvent, CaveOnboardingState, CaveRequest
from app.repositories.user import UserRepository
from app.services.transaction import rollback_on_error
from app.models.cultivation_retreat import CultivationRetreat
from app.models.todo import Task
from app.services import cultivation_retreat as retreat_lifecycle
from app.timezone import APP_TIMEZONE, as_utc


class CaveOnboardingService:
    def __init__(self, db):
        self.db = db

    def initialize(self, user_id):
        state = self.db.query(CaveOnboardingState).filter_by(user_id=user_id).first()
        if state is None:
            has_tasks = self.db.query(Task.id).filter_by(user_id=user_id).first() is not None
            used_cave = (self.db.query(CaveEvent.id).filter_by(user_id=user_id, event='cave_open').first() is not None or
                         self.db.query(CultivationRetreat.id).filter_by(user_id=user_id).first() is not None)
            state = CaveOnboardingState(user_id=user_id, status='not_required' if has_tasks or used_cave else 'pending',
                                        first_opened_at=retreat_lifecycle.utc_now())
            self.db.add(state)
            if state.status == 'pending':
                self.record_event(state, 'onboarding_start')
            self.db.flush()
        return state

    @rollback_on_error
    def skip(self, user_id, request_id):
        from app.services.cave import CaveService

        UserRepository(self.db).lock(user_id)
        previous = CaveService(self.db).replay(user_id, request_id, 'onboarding_skip', {})
        if previous is not None:
            self.db.commit()
            return previous
        state = self.db.query(CaveOnboardingState).filter_by(user_id=user_id).first()
        if state is None:
            raise HTTPException(status_code=409, detail='先回洞府，听小满说一声。')
        if state.status == 'pending':
            state.status = 'skipped'
            self.record_event(state, 'onboarding_skip')
        result = self.response(state)
        self.db.add(CaveRequest(user_id=user_id, request_id=request_id, operation='onboarding_skip', payload={}, result=result))
        self.db.commit()
        return result

    @rollback_on_error
    def complete(self, user_id, request_id, session_id):
        from app.services.cave import CaveService

        UserRepository(self.db).lock(user_id)
        service = CaveService(self.db)
        session = service.get_session(user_id, session_id)
        payload = {'session_id': str(session_id)}
        previous = service.replay(user_id, request_id, 'onboarding_complete', payload)
        if previous is not None:
            self.db.commit()
            return previous
        state = self.db.query(CaveOnboardingState).filter_by(user_id=user_id).first()
        if state is None:
            raise HTTPException(status_code=409, detail='先回洞府，听小满说一声。')
        if state.status == 'pending':
            if session.status != 'completed' or session.target_duration != 15 or as_utc(session.started_at) < as_utc(state.first_opened_at):
                raise HTTPException(status_code=409, detail='完成这一段十五分钟入定，再回来听小满说一声。')
            state.status = 'completed'
            state.completed_session_id = session.id
            self.record_event(state, 'onboarding_complete')
        result = self.response(state)
        self.db.add(CaveRequest(user_id=user_id, request_id=request_id, operation='onboarding_complete', payload=payload, result=result))
        self.db.commit()
        return result

    def snapshot(self, user_id):
        state = self.db.query(CaveOnboardingState).filter_by(user_id=user_id).first()
        return self.response(state) if state else None

    def response(self, state):
        return {'status': state.status,
                'completed_session_id': str(state.completed_session_id) if state.completed_session_id else None}

    def record_event(self, state, event):
        now = retreat_lifecycle.utc_now()
        hour = as_utc(now).astimezone(APP_TIMEZONE).hour
        mode = 'morning' if 5 <= hour < 11 else 'day' if 11 <= hour < 17 else 'dusk' if 17 <= hour < 21 else 'night'
        active = self.db.query(CultivationRetreat.id).filter_by(user_id=state.user_id, status='active').first() is not None
        self.db.add(CaveEvent(user_id=state.user_id, request_id=uuid4(), event=event, source='onboarding', mode=mode,
                              has_active_session=active, session_id=state.completed_session_id,
                              facts={'status': state.status}, created_at=now))
