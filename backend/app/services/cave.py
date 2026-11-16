from datetime import date, datetime, timezone
from hashlib import sha256

from fastapi import HTTPException
from sqlalchemy import JSON
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cave import CaveRequest, CaveEvent, CaveDailyState
from app.repositories.user import UserRepository
from app.services.transaction import rollback_on_error

from app.models.cultivation_retreat import CultivationRetreat
from app.models.todo import Task
from app.schemas.cultivation_retreat import RetreatResponse
from app.services.cultivation_retreat import CultivationRetreatService
from app.services import cultivation_retreat as retreat_lifecycle
from app.timezone import as_utc
from app.services.daily_workbench import DailyWorkbenchService


from app.services.content_catalog import CAVE_FORTUNES as FORTUNES


def session_response(session):
    if session is None:
        return None
    return RetreatResponse.model_validate(session).model_dump(mode='json')


class CaveService:
    def __init__(self, db: Session):
        self.db = db

    def replay(self, user_id, request_id, operation, payload):
        request = self.db.query(CaveRequest).filter_by(user_id=user_id, request_id=request_id).first()
        if request is None:
            return None
        if request.operation != operation or request.payload != payload:
            raise HTTPException(status_code=409, detail='这次请求已用于其他操作，请重新选择。')
        return request.result

    @rollback_on_error
    def start_session(self, user_id, data):
        payload = data.model_dump(mode='json', exclude={'request_id'})
        UserRepository(self.db).lock(user_id)
        previous = self.replay(user_id, data.request_id, 'start', payload)
        if previous is not None:
            self.db.commit()
            return previous
        active = CultivationRetreatService.get_active_retreat(self.db, user_id)
        if active is None:
            if data.todo_id:
                task = self.db.query(Task).filter_by(id=data.todo_id, user_id=user_id).first()
                if task is None:
                    raise HTTPException(status_code=404, detail='这件事暂时未找到，请重新选一件。')
                if task.status not in ('pending', 'in_progress'):
                    raise HTTPException(status_code=409, detail='这件事已告一段落，请重新选一件。')
            try:
                active = CultivationRetreatService.start_retreat(
                    self.db, user_id, data.target_duration, data.todo_id,
                    commit=False, mark_todo_complete=data.mark_todo_complete,
                )
            except HTTPException as error:
                if error.status_code != 409:
                    raise
                active = CultivationRetreatService.get_active_retreat(self.db, user_id)
                if active is None:
                    raise
        result = session_response(active)
        self.db.add(CaveRequest(user_id=user_id, request_id=data.request_id,
                                operation='start', payload=payload, result=result))
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            previous = self.replay(user_id, data.request_id, 'start', payload)
            if previous is None:
                raise
            return previous
        return result

    def get_session(self, user_id, session_id):
        session = self.db.query(CultivationRetreat).filter_by(id=session_id, user_id=user_id).first()
        if session is None:
            raise HTTPException(status_code=404, detail='这段入定暂时未找到。')
        return session

    def read_session(self, user_id, session_id):
        session = self.get_session(user_id, session_id)
        return {'session': session_response(session),
                'acknowledged': session.return_acknowledged_at is not None,
                'server_now': datetime.now(timezone.utc).isoformat()}

    def pending_return(self, user_id):
        session = self.db.query(CultivationRetreat).filter(
            CultivationRetreat.user_id == user_id,
            CultivationRetreat.return_acknowledged_at.is_(None),
            CultivationRetreat.return_summary.is_not(None),
            CultivationRetreat.return_summary != JSON.NULL,
            CultivationRetreat.status.in_(('completed', 'aborted')),
        ).order_by(CultivationRetreat.ended_at, CultivationRetreat.id).first()
        if session is not None:
            return {'session_id': str(session.id), 'status': 'unviewed', 'todo_title': session.todo_title}
        session = CultivationRetreatService.get_active_retreat(self.db, user_id)
        if session is not None:
            elapsed = (retreat_lifecycle.utc_now() - as_utc(session.started_at)).total_seconds()
            if elapsed >= session.target_duration * 60:
                return {'session_id': str(session.id), 'status': 'ready', 'todo_title': session.todo_title}
        return None

    @rollback_on_error
    def acknowledge_return(self, user_id, session_id, data):
        UserRepository(self.db).lock(user_id)
        payload = {'session_id': str(session_id)}
        previous = self.replay(user_id, data.request_id, 'acknowledge', payload)
        if previous is not None:
            self.db.commit()
            return previous
        session = self.get_session(user_id, session_id)
        if session.status not in ('completed', 'aborted'):
            raise HTTPException(status_code=409, detail='先收好这一段入定，再回洞府。')
        if session.return_acknowledged_at is None:
            session.return_acknowledged_at = retreat_lifecycle.utc_now()
        result = {'session_id': str(session_id), 'acknowledged': True}
        self.db.add(CaveRequest(user_id=user_id, request_id=data.request_id,
                                operation='acknowledge', payload=payload, result=result))
        self.db.commit()
        return result

    @rollback_on_error
    def settle_session(self, user_id, session_id, data):
        UserRepository(self.db).lock(user_id)
        payload = {'session_id': str(session_id), 'early': data.early}
        previous = self.replay(user_id, data.request_id, 'settle', payload)
        if previous is not None:
            self.db.commit()
            return previous
        session = self.get_session(user_id, session_id)
        if session.status == 'active' and not data.early:
            elapsed = (retreat_lifecycle.utc_now() - as_utc(session.started_at)).total_seconds()
            if elapsed < session.target_duration * 60 * 0.8:
                raise HTTPException(status_code=409, detail='先安心坐一会儿，或选择提前结束。')
        if data.early:
            session = CultivationRetreatService.abort_retreat(self.db, user_id, session_id, commit=False)
        else:
            session = CultivationRetreatService.complete_retreat(
                self.db, user_id, session_id, mark_todo_complete=session.mark_todo_complete, commit=False,
            )
        result = session_response(session)
        self.db.add(CaveRequest(user_id=user_id, request_id=data.request_id,
                                operation='settle', payload=payload, result=result))
        self.db.commit()
        return result

    def list_events(self, user_id, session_id, limit):
        query = self.db.query(CaveEvent).filter_by(user_id=user_id)
        if session_id is not None:
            query = query.filter_by(session_id=session_id)
        return [{'id': str(event.id), 'event': event.event, 'source': event.source,
                 'mode': event.mode, 'has_active_session': event.has_active_session,
                 'session_id': str(event.session_id) if event.session_id else None,
                 'facts': event.facts or {}, 'created_at': as_utc(event.created_at).isoformat()}
                for event in query.order_by(CaveEvent.created_at, CaveEvent.id).limit(limit).all()]

    @rollback_on_error
    def record_open(self, user_id, data):
        UserRepository(self.db).lock(user_id)
        session = self.get_session(user_id, data.session_id) if data.session_id is not None else None
        event = self.db.query(CaveEvent).filter_by(user_id=user_id, request_id=data.request_id).first()
        payload = data.model_dump(exclude={'request_id', 'notification_type', 'delay_ms'})
        notification = {'notification_type': data.notification_type, 'delay_ms': data.delay_ms} if data.event == 'notification_click' else {}
        if event is None:
            facts = {**notification, 'session_status': session.status} if notification else {}
            event = CaveEvent(user_id=user_id, request_id=data.request_id, facts=facts, **payload)
            self.db.add(event)
            self.db.flush()
        elif (any(getattr(event, key) != value for key, value in payload.items()) or
              any((event.facts or {}).get(key) != value for key, value in notification.items())):
            raise HTTPException(status_code=409, detail='这条来访记录已保存。')
        result = {'id': str(event.id), **payload}
        if notification:
            result.update(notification)
            result['facts'] = event.facts
        self.db.commit()
        return result

    def candidates(self, board):
        groups = board['task_groups']
        ranked = [
            ('逾期', groups['overdue']),
            ('今天到期', sorted(groups['today'], key=lambda task: {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}.get(task['priority'], 2))),
            ('进行中', [task for tasks in groups.values() for task in tasks if task['status'] == 'in_progress']),
            ('重要待办', [task for task in groups['unscheduled'] if task['priority'] in ('high', 'urgent')]),
            ('稍后到期', groups['upcoming']),
        ]
        seen, result = set(), []
        for source, tasks in ranked:
            for task in tasks:
                if task['id'] not in seen:
                    seen.add(task['id'])
                    result.append({**task, 'source': source})
        return result

    @rollback_on_error
    def reroll(self, user_id, data):
        UserRepository(self.db).lock(user_id)
        payload = data.model_dump(mode='json', exclude={'request_id'})
        previous = self.replay(user_id, data.request_id, 'reroll', payload)
        if previous is not None:
            self.db.commit()
            return previous
        board = DailyWorkbenchService(self.db).get_workbench(user_id)
        if data.date.isoformat() != board['date']:
            raise HTTPException(status_code=409, detail='山中已是新的一天，请刷新今日签。')
        state, signs = self.daily_state(user_id, board)
        if state.reroll_used:
            raise HTTPException(status_code=409, detail='今日已换签')
        replacement = next((task for task in self.candidates(board) if task['id'] not in state.sign_task_ids), None)
        if not signs or replacement is None:
            raise HTTPException(status_code=409, detail='签筒里暂时没有别的签，可以手动选一件事。')
        signs = [replacement, *signs[1:]]
        state.sign_task_ids = [task['id'] for task in signs]
        state.reroll_used = True
        result = self.snapshot(user_id, board, state, signs)
        self.db.add(CaveRequest(user_id=user_id, request_id=data.request_id,
                                operation='reroll', payload=payload, result=result))
        self.db.commit()
        return result

    @rollback_on_error
    def select_sign(self, user_id, data):
        UserRepository(self.db).lock(user_id)
        payload = data.model_dump(mode='json', exclude={'request_id'})
        previous = self.replay(user_id, data.request_id, 'select', payload)
        if previous is not None:
            self.db.commit()
            return previous
        board = DailyWorkbenchService(self.db).get_workbench(user_id)
        if data.date.isoformat() != board['date']:
            raise HTTPException(status_code=409, detail='山中已是新的一天，请刷新今日签。')
        task_id = str(data.task_id)
        task = next((task for tasks in board['task_groups'].values() for task in tasks if task['id'] == task_id), None)
        if task is None:
            raise HTTPException(status_code=404, detail='这件事已不在签筒中，请刷新后重新选。')
        state, signs = self.daily_state(user_id, board)
        selected = next((sign for sign in signs if sign['id'] == task_id), {**task, 'source': '签筒自选'})
        signs = [selected, *[sign for sign in signs if sign['id'] != task_id]][:3]
        state.sign_task_ids = [sign['id'] for sign in signs]
        state.had_signs = True
        result = self.snapshot(user_id, board, state, signs)
        self.db.add(CaveRequest(user_id=user_id, request_id=data.request_id,
                                operation='select', payload=payload, result=result))
        self.db.commit()
        return result

    def get_daily_state(self, user_id, plan_date):
        state = self.db.query(CaveDailyState).filter_by(user_id=user_id, plan_date=plan_date).populate_existing().first()
        if state is None:
            index = int(sha256(f'{user_id}:{plan_date.isoformat()}'.encode()).hexdigest(), 16) % len(FORTUNES)
            state = CaveDailyState(user_id=user_id, plan_date=plan_date, omen_key=FORTUNES[index]['key'],
                                   sign_task_ids=[], reroll_used=False, had_signs=False)
            self.db.add(state)
            self.db.flush()
        return state

    def daily_state(self, user_id, board):
        state = self.get_daily_state(user_id, date.fromisoformat(board['date']))
        all_open = {task['id']: task for tasks in board['task_groups'].values() for task in tasks}
        ranked = self.candidates(board)
        available = {task['id']: task for task in ranked}
        available.update({task_id: {**task, 'source': '签筒自选'} for task_id, task in all_open.items() if task_id not in available})
        ids = [task_id for task_id in state.sign_task_ids if task_id in available]
        for task in ranked:
            if len(ids) >= 3:
                break
            if task['id'] not in ids:
                ids.append(task['id'])
        state.sign_task_ids = ids
        state.had_signs = state.had_signs or bool(ids)
        self.db.flush()
        return state, [available[task_id] for task_id in ids]

    def snapshot(self, user_id, board, state, signs):
        from app.services.cave_companions import CaveCompanionService
        from app.services.cave_progression import get_companion_progress
        from app.services.cave_letters import CaveLetterService
        from app.services.cave_onboarding import CaveOnboardingService

        companions = CaveCompanionService(self.db).snapshot(user_id)
        return {
            'onboarding': CaveOnboardingService(self.db).snapshot(user_id),
            'unread_letters_count': CaveLetterService(self.db).unread_count(user_id),
            'companions': companions,
            'next_unlock': get_companion_progress(self.db, user_id)['next_unlock'],
            'daily_note': companions['daily_note'],
            'date': board['date'],
            'server_now': datetime.now(timezone.utc).isoformat(),
            'fortune': next(fortune for fortune in FORTUNES if fortune['key'] == state.omen_key),
            'primary_sign': signs[0] if signs else None,
            'signs': signs,
            'reroll_used': state.reroll_used,
            'all_signs_done': state.had_signs and not signs,
            'summary': board['summary'],
            'first_session': not self.db.query(CultivationRetreat.id).filter_by(user_id=user_id).first(),
            'active_session': session_response(CultivationRetreatService.get_active_retreat(self.db, user_id)),
            'pending_return': self.pending_return(user_id),
        }

    @rollback_on_error
    def get_cave(self, user_id):
        from app.services.cave_onboarding import CaveOnboardingService

        UserRepository(self.db).lock(user_id)
        CaveOnboardingService(self.db).initialize(user_id)
        board = DailyWorkbenchService(self.db).get_workbench(user_id)
        state, signs = self.daily_state(user_id, board)
        result = self.snapshot(user_id, board, state, signs)
        self.db.commit()
        return result
