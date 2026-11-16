"""Freeze the return receipt within the retreat's settlement transaction."""

from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

from app.models.cave import CaveDailyState, CaveEvent
from app.models.coin_transaction import CoinTransaction, CoinType
from app.models.cultivation_retreat import CultivationRetreat, UserEncounterRecord
from app.services.cave_progression import get_companion_progress
from app.services.content_catalog import CAVE_FORTUNES
from app.services.cultivation import CultivationService, REALM_ORDER
from app.services.encounter_engine import EncounterEngine
from app.timezone import APP_TIMEZONE, as_utc, day_bounds_utc, local_date


def _fortune_bonus(db, session):
    date = local_date(session.ended_at)
    state = db.query(CaveDailyState).filter_by(user_id=session.user_id, plan_date=date).first()
    index = int(sha256(f'{session.user_id}:{date.isoformat()}'.encode()).hexdigest(), 16) % len(CAVE_FORTUNES)
    fortune = next((item for item in CAVE_FORTUNES if state and item['key'] == state.omen_key), CAVE_FORTUNES[index])
    start, end = day_bounds_utc(date)
    prior = db.query(CultivationRetreat.id).filter(
        CultivationRetreat.user_id == session.user_id, CultivationRetreat.id != session.id,
        CultivationRetreat.qi_gained > 0,
        CultivationRetreat.ended_at >= start, CultivationRetreat.ended_at < end,
    ).first()
    applied = session.qi_gained > 0 and prior is None
    bonus = session.exp_gained // 10 if applied else 0
    reward = CultivationService(db).settle_todo_reward(
        session.user_id, 'retreat_omen', bonus, 'medium',
        source_key=f'retreat_omen:{session.id}', fixed_spirit_stones=0,
    ).model_dump(mode='json') if applied else None
    return {'key': fortune['key'], 'title': fortune['title'], 'date': date.isoformat(),
            'multiplier': 1.1, 'applied': applied, 'bonus_cultivation': bonus, 'reward': reward}


def _encounter(db, session):
    if session.status != 'completed':
        return None, None
    previous = db.query(CultivationRetreat.ended_at).filter(
        CultivationRetreat.user_id == session.user_id, CultivationRetreat.id != session.id,
        CultivationRetreat.status == 'completed',
    ).all()
    dates = {local_date(row.ended_at) for row in previous if row.ended_at is not None}
    date = local_date(session.ended_at)
    dates.add(date)
    streak = 0
    while date in dates:
        streak += 1
        date -= timedelta(days=1)
    service = CultivationService(db)
    profile = service.ensure_profile(session.user_id)
    realm_level = REALM_ORDER.index(profile.realm_key) + 1
    EncounterEngine.seed_events(db, commit=False)
    event = EncounterEngine.roll_encounter(
        db, str(session.user_id), realm_level=realm_level,
        duration_minutes=min(session.actual_duration, session.target_duration), streak_days=streak,
        force_hit=not previous, rarity='common' if not previous else None,
    )
    if event is None:
        return None, None
    record = db.query(UserEncounterRecord).filter_by(user_id=session.user_id, encounter_id=event.id).first()
    first = record is None
    if first:
        db.add(UserEncounterRecord(user_id=session.user_id, encounter_id=event.id, last_retreat_id=session.id))
    else:
        record.unlock_count += 1
        record.last_retreat_id = session.id
    session.encounter_id = event.id
    session.encounter_result = {
        'id': event.id, 'title': event.title, 'story_text': event.story_text, 'rarity': event.rarity,
        'reward_type': event.reward_type, 'reward_payload': event.reward_payload,
        'first_unlock': first, 'reward_suppressed': session.qi_gained == 0,
    }
    reward = None
    if session.qi_gained > 0:
        payload = event.reward_payload or {}
        reward = service.settle_todo_reward(
            session.user_id, 'retreat_encounter', payload.get('exp', 0), 'medium',
            source_key=f'retreat_encounter:{session.id}', fixed_spirit_stones=payload.get('coins', 0),
        ).model_dump(mode='json')
        if reward['spirit_stones'] > 0:
            db.add(CoinTransaction(user_id=session.user_id, amount=reward['spirit_stones'],
                                   type=CoinType.EARN.value, source='retreat_encounter', source_id=str(session.id),
                                   description=f'入定奇遇：{event.title}'))
    return reward, {'id': event.id, 'title': event.title} if first else None


def freeze_return(db, session):
    instant = as_utc(session.ended_at).astimezone(APP_TIMEZONE)
    hour = instant.hour
    mode = 'morning' if 5 <= hour < 11 else 'day' if 11 <= hour < 17 else 'dusk' if 17 <= hour < 21 else 'night'
    early = session.status == 'aborted'
    fortune_bonus = _fortune_bonus(db, session)
    encounter_reward, first_codex_unlock = _encounter(db, session)
    rewards = [session.settlement_result['retreat_reward'], session.settlement_result.get('task_reward'),
               fortune_bonus['reward'], encounter_reward]
    place = {'morning': '晨光里', 'day': '日光里', 'dusk': '暮色里', 'night': '灯下'}[mode]
    duration = f'坐了 {session.actual_duration} 分钟' if session.actual_duration else '留了一小会儿'
    narrative = (f'{place}{duration}，收得 {session.qi_gained} 灵气。这一段也算数，慢慢来。' if early
                 else f'{place}{duration}，这一段专注已稳稳收好。')
    companion = session.companion_snapshot
    if companion:
        narrative += f"{companion['name']}陪你坐过这一段时光。"
    summary = {
        'narrative': narrative,
        'context': {'mode': mode, 'actual_duration': session.actual_duration, 'early': early, 'companion': companion},
        'total_reward': {key: sum(reward.get(key, 0) for reward in rewards if reward)
                         for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state_delta')},
        'base_conversion': {'qi': session.qi_gained, 'cultivation': session.exp_gained,
                            'rate': session.settlement_result['conversion_rate']},
        'fortune_bonus': fortune_bonus,
        'encounter_reward': encounter_reward,
        'first_codex_unlock': first_codex_unlock,
        'next_unlock': get_companion_progress(db, session.user_id)['next_unlock'],
    }
    facts = {'actual_duration': session.actual_duration, 'qi': session.qi_gained,
             'base_cultivation': session.exp_gained, 'total_cultivation': summary['total_reward']['cultivation'],
             'total_spirit_stones': summary['total_reward']['spirit_stones'],
             'encounter_id': session.encounter_id, 'task_completed': session.settlement_result['task_completed']}
    db.add(CaveEvent(user_id=session.user_id, request_id=uuid4(), session_id=session.id,
                     event='retreat_early_end' if early else 'retreat_complete', source='settlement',
                     mode=mode, has_active_session=False, facts=facts, created_at=session.ended_at))
    if first_codex_unlock:
        db.add(CaveEvent(user_id=session.user_id, request_id=uuid4(), session_id=session.id,
                         event='codex_unlock', source='settlement', mode=mode, has_active_session=False,
                         facts={'encounter_id': session.encounter_id, 'rarity': session.encounter_result['rarity']},
                         created_at=session.ended_at))
    return summary
