from datetime import datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import func

from app.models.cave import CaveLetter, CaveRequest, CaveTrialAcceptance
from app.models.cultivation_retreat import CultivationRetreat
from app.models.todo import Habit, Task
from app.models.user import User
from app.repositories.user import UserRepository
from app.services import cultivation_retreat as retreat_lifecycle
from app.services.transaction import rollback_on_error
from app.timezone import APP_TIMEZONE, as_utc, day_start_utc, local_date


SENIORS = {
    'qingheng': {'name': '师姐·青蘅', 'day': 7, 'trials': ('quiet_night', 'early_rest')},
    'lifeng': {'name': '师兄·砺锋', 'day': 14, 'trials': ('old_task', 'long_sitting')},
}
TRIALS = {
    'quiet_night': {'key': 'quiet_night', 'title': '留一晚灯火', 'description': '接受后，在本周完成一次夜间 25 分钟入定。', 'target': 1},
    'early_rest': {'key': 'early_rest', 'title': '三夜早眠', 'description': '接受后，在本周连续 3 个中国日于 22:30 前收功。', 'target': 3},
    'old_task': {'key': 'old_task', 'title': '重拾旧事', 'description': '接受后，在本周完成一件已放下超过 3 天的任务。', 'target': 1},
    'long_sitting': {'key': 'long_sitting', 'title': '一段长定', 'description': '接受后，在本周完成一次 90 分钟入定。', 'target': 1},
}


class CaveLetterService:
    def __init__(self, db):
        self.db = db

    @rollback_on_error
    def get_letters(self, user_id):
        UserRepository(self.db).lock(user_id)
        self.deliver(user_id)
        result = self.snapshot(user_id)
        self.db.commit()
        return result

    def owned_letter(self, user_id, letter_id):
        row = self.db.query(CaveLetter).filter_by(user_id=user_id, id=letter_id).first()
        if row is None:
            raise HTTPException(status_code=404, detail='这封山中来信暂未找到。')
        return row

    def get_letter(self, user_id, letter_id):
        return self.letter_response(self.owned_letter(user_id, letter_id))

    @rollback_on_error
    def act(self, user_id, letter_id, action, request_id):
        from app.services.cave import CaveService

        UserRepository(self.db).lock(user_id)
        row = self.owned_letter(user_id, letter_id)
        payload = {'letter_id': str(letter_id)}
        previous = CaveService(self.db).replay(user_id, request_id, f'letter_{action}', payload)
        if previous is not None:
            self.db.commit()
            return previous
        now = retreat_lifecycle.utc_now()
        state = dict(row.state)
        state.setdefault('read_at', now.isoformat())
        if action == 'accept':
            selected = self.acceptance(user_id, row.week_start)
            if row.week_start != self.current_week() or state.get('declined_at') or (selected and selected.letter_id != row.id):
                raise HTTPException(status_code=409, detail='本周只选一个试炼就好，下周还会有新的来信。')
            if selected is None:
                self.db.add(CaveTrialAcceptance(user_id=user_id, week_start=row.week_start, letter_id=row.id, accepted_at=now))
                state['accepted_at'] = now.isoformat()
        if action == 'decline':
            if state.get('accepted_at'):
                raise HTTPException(status_code=409, detail='这一周的试炼已选好，不必急着更换。')
            state.setdefault('declined_at', now.isoformat())
        if action == 'claim' and not state.get('completed_at'):
            if not state.get('accepted_at') or self.progress(row) < row.content['trial']['target']:
                raise HTTPException(status_code=409, detail='试炼还在路上，完成后再来收下这页故事。')
            state['completed_at'] = now.isoformat()
            trial = row.content['trial']
            state['reward'] = {'kind': 'codex', 'key': f"trial:{trial['key']}", 'name': trial['title'],
                               'story': f"完成「{trial['title']}」的这一周，被郑重收进山中书页。"}
        row.state = state
        self.db.flush()
        result = self.snapshot(user_id)
        self.db.add(CaveRequest(user_id=user_id, request_id=request_id, operation=f'letter_{action}', payload=payload, result=result))
        self.db.commit()
        return result

    def deliver(self, user_id):
        now = retreat_lifecycle.utc_now()
        date = local_date(now)
        user = self.db.query(User).filter_by(id=user_id).one()
        week = date - timedelta(days=date.weekday())
        for key, senior in SENIORS.items():
            first_date = local_date(user.created_at) + timedelta(days=senior['day'] - 1)
            first_week = first_date - timedelta(days=first_date.weekday())
            if date < first_date or (week != first_week and now < datetime.combine(week, time(8), APP_TIMEZONE)):
                continue
            previous = self.db.query(CaveLetter).filter_by(user_id=user_id, senior_key=key, week_start=week).first()
            if previous is None:
                facts = self.weekly_facts(user_id, week, now)
                latest = facts['latest_completion_time'] or '尚无记录'
                body = (f"这一周完成了 {facts['completed_tasks']} 件，最长连续 {facts['best_streak']} 天。"
                        f"最晚完成时间{latest}，本周入定 {facts['weekly_sessions']} 次。")
                self.db.add(CaveLetter(user_id=user_id, senior_key=key, week_start=week, delivered_at=now,
                    content={'title': f"{senior['name']}的山中来信",
                             'body': body + ('慢慢来，这一段路也有人陪着你。' if key == 'qingheng' else '选定一件，踏实去做；暂不接受也无妨。'),
                             'variables': facts,
                             'trial': TRIALS[senior['trials'][((week - first_week).days // 7) % 2]]},
                    state={}))
                self.db.flush()

    def seniors_snapshot(self, user_id):
        self.deliver(user_id)
        rows = self.db.query(CaveLetter).filter_by(user_id=user_id).all()
        result = []
        for key, senior in SENIORS.items():
            delivered = [as_utc(row.delivered_at).isoformat() for row in rows if row.senior_key == key]
            result.append({'key': key, 'name': senior['name'], 'unlocked': bool(delivered),
                           'hint': f"第 {senior['day']} 天，{'师姐' if key == 'qingheng' else '师兄'}会寄来第一封信。",
                           'rarity': 'rare', 'story': '山中同门，书信相伴。',
                           'first_unlocked_at': min(delivered) if delivered else None, 'unlock_count': len(delivered)})
        return result

    def unread_count(self, user_id):
        return sum(not row.state.get('read_at') for row in self.db.query(CaveLetter.state).filter_by(user_id=user_id))

    def codex_stories(self, user_id):
        rows = self.db.query(CaveLetter).filter_by(user_id=user_id).all()
        entries = []
        for key, trial in TRIALS.items():
            completed = [row for row in rows if row.content['trial']['key'] == key and row.state.get('completed_at')]
            reward = completed[0].state['reward'] if completed else {
                'key': f'trial:{key}', 'name': trial['title'], 'story': f"完成「{trial['title']}」的这一周，被郑重收进山中书页。"}
            entries.append({**{field: reward[field] for field in ('key', 'name', 'story')}, 'rarity': 'rare',
                            'hint': '接受并完成同门试炼，收下这一页故事。', 'unlocked': bool(completed),
                            'first_unlocked_at': min(row.state['completed_at'] for row in completed) if completed else None,
                            'unlock_count': len(completed)})
        return entries

    def weekly_facts(self, user_id, week, now):
        start = day_start_utc(week)
        completed = self.db.query(Task.completed_at).filter(
            Task.user_id == user_id, Task.status == 'completed', Task.completed_at >= start, Task.completed_at <= now,
        ).all()
        latest = max((as_utc(row.completed_at).astimezone(APP_TIMEZONE).strftime('%H:%M') for row in completed), default=None)
        sessions = self.db.query(CultivationRetreat).filter(
            CultivationRetreat.user_id == user_id, CultivationRetreat.status == 'completed',
            CultivationRetreat.ended_at >= start, CultivationRetreat.ended_at <= now,
        ).count()
        streak = self.db.query(func.coalesce(func.max(Habit.best_streak), 0)).filter(Habit.user_id == user_id).scalar()
        return {'completed_tasks': len(completed), 'best_streak': streak, 'latest_completion_time': latest, 'weekly_sessions': sessions}

    def progress(self, row):
        if row.state.get('completed_at'):
            return row.content['trial']['target']
        if not row.state.get('accepted_at'):
            return 0
        start = datetime.fromisoformat(row.state['accepted_at'])
        end = day_start_utc(row.week_start + timedelta(days=7))
        if row.content['trial']['key'] == 'old_task':
            tasks = self.db.query(Task).filter(
                Task.user_id == row.user_id, Task.status == 'completed',
                Task.completed_at >= start, Task.completed_at < end,
                Task.completed_at <= retreat_lifecycle.utc_now(),
            ).all()
            return int(any(as_utc(task.completed_at) - as_utc(task.created_at) > timedelta(days=3) for task in tasks))
        sessions = self.db.query(CultivationRetreat).filter(
            CultivationRetreat.user_id == row.user_id, CultivationRetreat.status == 'completed',
            CultivationRetreat.started_at >= start, CultivationRetreat.ended_at < end,
            CultivationRetreat.ended_at <= retreat_lifecycle.utc_now(),
        ).all()
        if row.content['trial']['key'] == 'quiet_night':
            return int(any(session.actual_duration >= 25 and session.target_duration >= 25 and
                           (as_utc(session.started_at).astimezone(APP_TIMEZONE).hour >= 21 or
                            as_utc(session.started_at).astimezone(APP_TIMEZONE).hour < 5) for session in sessions))
        if row.content['trial']['key'] == 'long_sitting':
            return int(any(session.actual_duration >= 90 and session.target_duration >= 90 for session in sessions))
        if row.content['trial']['key'] == 'early_rest':
            dates = sorted({local_date(session.ended_at) for session in sessions
                            if as_utc(session.ended_at).astimezone(APP_TIMEZONE).time() < time(22, 30)})
            longest = streak = 0
            previous = None
            for date in dates:
                streak = streak + 1 if previous and date == previous + timedelta(days=1) else 1
                longest = max(longest, streak)
                previous = date
            return min(3, longest)
        return 0

    def current_week(self):
        date = local_date(retreat_lifecycle.utc_now())
        return date - timedelta(days=date.weekday())

    def acceptance(self, user_id, week):
        return self.db.query(CaveTrialAcceptance).filter_by(user_id=user_id, week_start=week).first()

    def snapshot(self, user_id):
        rows = self.db.query(CaveLetter).filter_by(user_id=user_id).order_by(CaveLetter.delivered_at.desc(), CaveLetter.senior_key).all()
        selected = self.acceptance(user_id, self.current_week())
        accepted = next((row for row in rows if selected and row.id == selected.letter_id), None)
        return {'letters': [self.letter_response(row) for row in rows],
                'unread_count': sum(not row.state.get('read_at') for row in rows),
                'accepted_trial': {'letter_id': str(accepted.id), 'week_start': accepted.week_start.isoformat(),
                                   'status': 'completed' if accepted.state.get('completed_at') else 'accepted'} if accepted else None}

    def letter_response(self, row):
        selected = self.acceptance(row.user_id, row.week_start)
        status = ('completed' if row.state.get('completed_at') else 'accepted' if row.state.get('accepted_at')
                  else 'declined' if row.state.get('declined_at') else 'read' if row.state.get('read_at') else 'unread')
        current = self.progress(row)
        trial_status = ('ready' if status == 'accepted' and current >= row.content['trial']['target'] else status
                        if status in ('accepted', 'declined', 'completed') else 'available')
        can_accept = row.week_start == self.current_week() and selected is None and not row.state.get('declined_at')
        return {'id': str(row.id), 'senior_key': row.senior_key, 'senior_name': SENIORS[row.senior_key]['name'],
                'week_start': row.week_start.isoformat(), 'delivered_at': as_utc(row.delivered_at).isoformat(),
                'read_at': row.state.get('read_at'), 'status': status, **row.content,
                'trial': {**row.content['trial'], 'current': current, 'status': trial_status,
                          'can_accept': can_accept, 'reward': row.state.get('reward')}}
