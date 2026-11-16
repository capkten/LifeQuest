from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def return_clock(monkeypatch, clock):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]
    monkeypatch.setattr('app.services.cultivation_retreat.utc_now', lambda: instant[0])
    monkeypatch.setattr('app.services.encounter_engine.random.random', lambda: 1.0)

    def advance(minutes=0, *, at=None):
        instant[0] = at if at is not None else instant[0] + timedelta(minutes=minutes)
        clock(instant[0])
        return instant[0]

    advance()
    return advance


def start_session(client, auth, minutes=25, **values):
    response = client.post('/api/cave/sessions', headers=auth, json={
        'target_duration': minutes, 'request_id': str(uuid4()), **values,
    })
    assert response.status_code == 200, response.text
    return response.json()


def settle_session(client, auth, session, early=False):
    response = client.post(f'/api/cave/sessions/{session["id"]}/settle', headers=auth,
                           json={'request_id': str(uuid4()), 'early': early})
    assert response.status_code == 200, response.text
    return response.json()


def test_zero_minute_return_has_a_frozen_zero_reward_summary_without_passive_rewards(
    client, auth_headers, return_clock,
):
    session = start_session(client, auth_headers)
    receipt = settle_session(client, auth_headers, session, early=True)
    summary = receipt['return_summary']
    assert summary['total_reward'] == {
        'cultivation': 0, 'spirit_stones': 0, 'merit': 0, 'mind_state_delta': 0,
    }
    assert summary['base_conversion'] == {'qi': 0, 'cultivation': 0, 'rate': 0.25}
    assert summary['encounter_reward'] is None
    assert summary['fortune_bonus']['applied'] is False
    assert summary['context'] == {'mode': 'morning', 'actual_duration': 0, 'early': True, 'companion': None}
    assert summary['next_unlock'] == {'key': 'white_deer', 'name': '白鹿·衔芝', 'current': 0, 'target': 3, 'unlocked': False}
    assert '0 灵气' in summary['narrative']
    assert '未结丹' not in summary['narrative']
    assert '晨光' in summary['narrative']
    return_clock(1500)
    replay = client.post(f'/api/cultivation/retreat/{session["id"]}/complete', headers=auth_headers)
    assert replay.status_code == 200
    assert replay.json() == receipt


def test_first_success_after_an_early_end_guarantees_common_and_freezes_separate_task_omen_encounter_rewards(
    client, auth_headers, return_clock, monkeypatch,
):
    monkeypatch.setattr('app.services.encounter_engine.random.choices',
                        lambda population, **options: [next(item for item in population if item.id == 'enc_epiphany_01')])
    early = start_session(client, auth_headers)
    settle_session(client, auth_headers, early, early=True)
    task = client.post('/api/todos/tasks', headers=auth_headers, json={'title': '写完周报'}).json()
    session = start_session(client, auth_headers, todo_id=task['id'])
    return_clock(25)
    response = client.post(f'/api/cultivation/retreat/{session["id"]}/complete', headers=auth_headers,
                           json={'mark_todo_complete': True})
    assert response.status_code == 200, response.text
    receipt = response.json()
    encounter = receipt['encounter_result']
    assert encounter['id'] == 'enc_epiphany_01'
    assert (encounter['rarity'], encounter['first_unlock'], encounter['reward_payload']) == ('common', True, {'exp': 50})
    assert encounter['story_text']
    summary = receipt['return_summary']
    assert (receipt['exp_gained'], receipt['coins_gained']) == (12, 7)
    assert receipt['settlement_result']['task_reward']['cultivation'] == 15
    assert summary['fortune_bonus']['bonus_cultivation'] == 1
    assert (summary['encounter_reward']['cultivation'], summary['encounter_reward']['spirit_stones'], summary['encounter_reward']['aptitude_points']) == (50, 0, 0)
    assert summary['total_reward'] == {'cultivation': 78, 'spirit_stones': 16, 'merit': 3, 'mind_state_delta': 1}
    assert summary['first_codex_unlock'] == {'id': 'enc_epiphany_01', 'title': '灵台空明'}
    catalog = client.get('/api/cultivation/retreat/encounters/catalog', headers=auth_headers).json()
    assert next(item for item in catalog if item['id'] == 'enc_epiphany_01')['unlock_count'] == 1
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    assert (before['cultivation'], before['spirit_stones'], before['aptitude_points']) == (78, 16, 1)
    return_clock(1500)
    assert settle_session(client, auth_headers, session, early=True) == receipt
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'aptitude_points', 'recent_rewards'):
        assert after[key] == before[key]


def test_first_success_with_zero_whole_minutes_unlocks_common_story_but_no_passive_resources(
    client, auth_headers, return_clock,
):
    session = start_session(client, auth_headers, minutes=1)
    return_clock(at=datetime(2026, 9, 12, 2, 0, 48, tzinfo=timezone.utc))
    receipt = settle_session(client, auth_headers, session)
    assert receipt['status'] == 'completed'
    assert receipt['qi_gained'] == 0
    assert receipt['encounter_result']['rarity'] == 'common'
    assert receipt['encounter_result']['reward_suppressed'] is True
    assert receipt['encounter_result']['reward_payload'] in ({'exp': 50}, {'exp': 75}, {'coins': 60})
    assert receipt['return_summary']['first_codex_unlock'] is not None
    assert receipt['return_summary']['encounter_reward'] is None
    assert receipt['return_summary']['total_reward'] == {'cultivation': 0, 'spirit_stones': 0, 'merit': 0, 'mind_state_delta': 0}
    assert receipt['return_summary']['fortune_bonus']['applied'] is False
    next_session = start_session(client, auth_headers)
    return_clock(25)
    assert settle_session(client, auth_headers, next_session)['encounter_result'] is None


def test_later_encounters_keep_engine_probability_and_credit_the_catalog_currency_exactly(
    client, auth_headers, return_clock, monkeypatch,
):
    first = start_session(client, auth_headers)
    return_clock(25)
    settle_session(client, auth_headers, first)
    # A 25-minute session and one China focus day have a 21% encounter chance.
    monkeypatch.setattr('app.services.encounter_engine.random.random', lambda: 0.22)
    second = start_session(client, auth_headers)
    return_clock(25)
    assert settle_session(client, auth_headers, second)['encounter_result'] is None
    monkeypatch.setattr('app.services.encounter_engine.random.random', lambda: 0.20)
    monkeypatch.setattr('app.services.encounter_engine.random.choices',
                        lambda population, **options: [next(item for item in population if item.id == 'enc_lingzhi_01')])
    third = start_session(client, auth_headers)
    return_clock(25)
    receipt = settle_session(client, auth_headers, third)
    assert receipt['encounter_result']['reward_payload'] == {'coins': 60}
    assert receipt['return_summary']['encounter_reward']['cultivation'] == 0
    assert receipt['return_summary']['encounter_reward']['spirit_stones'] == 60
    assert receipt['return_summary']['total_reward'] == {'cultivation': 6, 'spirit_stones': 63, 'merit': 2, 'mind_state_delta': 1}


@pytest.mark.parametrize('hour,minutes,mode,word', [
    (2, 45, 'morning', '晨光'), (4, 25, 'day', '日光'),
    (9, 25, 'dusk', '暮色'), (13, 25, 'night', '灯下'),
])
def test_success_narrative_freezes_the_china_settlement_scene_and_actual_duration(
    client, auth_headers, return_clock, hour, minutes, mode, word,
):
    return_clock(at=datetime(2026, 9, 12, hour, tzinfo=timezone.utc))
    session = start_session(client, auth_headers, minutes=minutes)
    return_clock(minutes)
    receipt = settle_session(client, auth_headers, session)
    summary = receipt['return_summary']
    assert summary['context'] == {'mode': mode, 'actual_duration': minutes, 'early': False, 'companion': None}
    assert word in summary['narrative']
    assert f'{minutes} 分钟' in summary['narrative']
    return_clock(1500)
    assert client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers).json()['session'] == receipt


def test_first_positive_qi_settlement_each_china_day_gets_only_a_recorded_ten_percent_base_bonus(
    client, auth_headers, return_clock,
):
    session = start_session(client, auth_headers, minutes=60)
    return_clock(45)
    receipt = settle_session(client, auth_headers, session, early=True)
    bonus = receipt['return_summary']['fortune_bonus']
    assert (receipt['qi_gained'], receipt['exp_gained'], receipt['coins_gained']) == (45, 11, 6)
    assert (bonus['date'], bonus['multiplier'], bonus['applied'], bonus['bonus_cultivation']) == ('2026-09-12', 1.1, True, 1)
    assert bonus['reward']['cultivation'] == 1
    assert bonus['reward']['spirit_stones'] == bonus['reward']['merit'] == bonus['reward']['aptitude_points'] == bonus['reward']['mind_state_delta'] == 0
    assert receipt['return_summary']['total_reward'] == {'cultivation': 12, 'spirit_stones': 6, 'merit': 2, 'mind_state_delta': 1}
    logs = client.get('/api/cultivation/overview', headers=auth_headers).json()['recent_rewards']
    assert next(log for log in logs if log['source'] == 'retreat_omen')['cultivation'] == 1
    session = start_session(client, auth_headers, minutes=60)
    return_clock(45)
    assert settle_session(client, auth_headers, session, early=True)['return_summary']['fortune_bonus']['applied'] is False
    return_clock(at=datetime(2026, 9, 12, 15, 15, tzinfo=timezone.utc))
    crossing = start_session(client, auth_headers, minutes=60)
    return_clock(45)
    bonus = settle_session(client, auth_headers, crossing, early=True)['return_summary']['fortune_bonus']
    assert (bonus['date'], bonus['applied'], bonus['bonus_cultivation']) == ('2026-09-13', True, 1)


@pytest.mark.parametrize('count,expected', [
    (3, {'key': 'spirit_fox', 'name': '灵狐·照夜', 'current': 3, 'target': 7, 'unlocked': False}),
    (7, {'key': 'cloud_crane', 'name': '玄鹤·临风', 'current': 7, 'target': 14, 'unlocked': False}),
    (14, None),
])
def test_next_unlock_advances_through_the_deer_fox_and_crane_then_finishes(
    client, auth_headers, return_clock, count, expected,
):
    for _ in range(count):
        session = start_session(client, auth_headers)
        return_clock(25)
        receipt = settle_session(client, auth_headers, session)
    assert receipt['return_summary']['next_unlock'] == expected


def test_expired_active_session_remains_ready_after_a_day_without_reward_decay(client, auth_headers, return_clock):
    session = start_session(client, auth_headers)
    return_clock(1500)
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return'] == {
        'session_id': session['id'], 'status': 'ready', 'todo_title': None,
    }
    receipt = settle_session(client, auth_headers, session)
    assert (receipt['qi_gained'], receipt['exp_gained'], receipt['coins_gained']) == (25, 6, 3)
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return']['status'] == 'unviewed'


def test_settlement_records_one_authoritative_event_and_replays_do_not_record_it_again(
    client, auth_headers, return_clock,
):
    session = start_session(client, auth_headers)
    receipt = settle_session(client, auth_headers, session, early=True)
    response = client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']})
    assert response.status_code == 200, response.text
    events = response.json()
    assert len(events) == 1
    event = events[0]
    assert event['event'] == 'retreat_early_end'
    assert event['session_id'] == session['id']
    assert event['facts'] == {
        'actual_duration': 0, 'qi': 0, 'base_cultivation': 0, 'total_cultivation': 0,
        'total_spirit_stones': 0, 'encounter_id': None, 'task_completed': False,
    }
    assert settle_session(client, auth_headers, session) == receipt
    assert client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json() == events


def test_return_view_is_an_explicit_idempotent_event_and_never_acknowledges_the_receipt(
    client, auth_headers, return_clock,
):
    session = start_session(client, auth_headers)
    settle_session(client, auth_headers, session, early=True)
    payload = {'event': 'return_view', 'session_id': session['id'], 'request_id': str(uuid4()),
               'source': 'return_page', 'mode': 'morning', 'has_active_session': False}
    response = client.post('/api/cave/events', headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    assert client.post('/api/cave/events', headers=auth_headers, json=payload).json() == response.json()
    events = client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json()
    assert [event['event'] for event in events].count('return_view') == 1
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return']['session_id'] == session['id']
    assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'session_id': str(uuid4()), 'request_id': str(uuid4())}).status_code == 404
    assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'session_id': None, 'request_id': str(uuid4())}).status_code == 422


def test_return_events_and_acknowledgements_are_owner_scoped(client, auth_headers, return_clock, db_session):
    from app.models.user import User
    from app.services.auth import create_access_token

    session = start_session(client, auth_headers)
    return_clock(25)
    settle_session(client, auth_headers, session)
    events = client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json()
    assert sorted(event['event'] for event in events) == ['codex_unlock', 'retreat_complete']
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    db_session.add(other)
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    assert client.get('/api/cave/events', headers=other_auth).json() == []
    assert client.get('/api/cave/events', headers=other_auth, params={'session_id': session['id']}).json() == []
    assert client.post('/api/cave/events', headers=other_auth, json={
        'event': 'return_view', 'session_id': session['id'], 'request_id': str(uuid4()),
        'source': 'return_page', 'mode': 'morning', 'has_active_session': False,
    }).status_code == 404
    assert client.post(f'/api/cave/sessions/{session["id"]}/acknowledge', headers=other_auth,
                       json={'request_id': str(uuid4())}).status_code == 404
    assert client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json() == events
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return']['session_id'] == session['id']
    assert client.get('/api/cave/events', headers=auth_headers, params={'limit': 101}).status_code == 422


def test_unviewed_return_survives_new_requests_and_a_day_until_explicit_acknowledgement(
    client, auth_headers, return_clock,
):
    session = start_session(client, auth_headers)
    receipt = settle_session(client, auth_headers, session, early=True)
    marker = {'session_id': session['id'], 'status': 'unviewed', 'todo_title': None}
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return'] == marker
    return_clock(1500)
    detail = client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers).json()
    assert detail['session'] == receipt
    assert detail['acknowledged'] is False
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return'] == marker
    payload = {'request_id': str(uuid4())}
    endpoint = f'/api/cave/sessions/{session["id"]}/acknowledge'
    response = client.post(endpoint, headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {'session_id': session['id'], 'acknowledged': True}
    assert client.post(endpoint, headers=auth_headers, json=payload).json() == response.json()
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return'] is None
    detail = client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers).json()
    assert detail['acknowledged'] is True
    assert detail['session'] == receipt


def test_acknowledging_the_oldest_return_exposes_the_next_unviewed_receipt(client, auth_headers, return_clock):
    first = start_session(client, auth_headers)
    first_receipt = settle_session(client, auth_headers, first, early=True)
    return_clock(1)
    second = start_session(client, auth_headers)
    second_receipt = settle_session(client, auth_headers, second, early=True)
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return']['session_id'] == first['id']
    for session, receipt in [(first, first_receipt), (second, second_receipt)]:
        response = client.post(f'/api/cave/sessions/{session["id"]}/acknowledge', headers=auth_headers,
                               json={'request_id': str(uuid4())})
        assert response.status_code == 200
        assert client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers).json()['session'] == receipt
        pending = client.get('/api/cave/today', headers=auth_headers).json()['pending_return']
        assert (pending['session_id'] if pending else None) == (second['id'] if session is first else None)


@pytest.mark.parametrize('rule_version', [None, 'b_v1'])
def test_historical_terminal_sessions_never_gain_return_extras_when_read_or_replayed(
    client, auth_headers, return_clock, db_session, user, rule_version,
):
    from app.models.cultivation_retreat import CultivationRetreat

    historical = CultivationRetreat(user_id=user.id, target_duration=25, status='completed',
                                   started_at=datetime(2026, 9, 11, 2), ended_at=datetime(2026, 9, 11, 2, 25),
                                   actual_duration=25, rule_version=rule_version, exp_gained=333, coins_gained=222)
    db_session.add(historical)
    db_session.commit()
    session_id = str(historical.id)
    receipt = client.get(f'/api/cave/sessions/{session_id}', headers=auth_headers).json()['session']
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    assert receipt['return_summary'] is None
    for operation in ['complete', 'abort']:
        response = client.post(f'/api/cultivation/retreat/{session_id}/{operation}', headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == receipt
    assert client.get('/api/cultivation/overview', headers=auth_headers).json() == before
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return'] is None
    assert client.get('/api/cave/events', headers=auth_headers).json() == []


def test_passive_return_logs_do_not_spend_any_of_the_eight_daily_task_aptitude_rewards(
    client, auth_headers, return_clock,
):
    return_clock(at=datetime.now(timezone.utc) - timedelta(minutes=25))
    session = start_session(client, auth_headers)
    return_clock(25)
    receipt = settle_session(client, auth_headers, session)
    assert receipt['return_summary']['fortune_bonus']['applied'] is True
    assert receipt['return_summary']['encounter_reward'] is not None
    for index in range(9):
        task = client.post('/api/todos/tasks', headers=auth_headers, json={'title': f'小事 {index}'}).json()
        completed = client.post(f'/api/todos/tasks/{task["id"]}/complete', headers=auth_headers)
        assert completed.status_code == 200, completed.text
        assert completed.json()['cultivation_reward']['aptitude_points'] == (1 if index < 8 else 0)
    assert client.get('/api/cultivation/overview', headers=auth_headers).json()['aptitude_points'] == 8


def test_failure_recording_the_codex_event_rolls_back_task_all_rewards_and_the_receipt(
    client, auth_headers, return_clock, db_session,
):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    task = client.post('/api/todos/tasks', headers=auth_headers, json={'title': '稳稳收好'}).json()
    session = start_session(client, auth_headers, todo_id=task['id'])
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    return_clock(25)
    db_session.execute(text("CREATE TRIGGER reject_codex BEFORE INSERT ON cave_events "
                            "WHEN NEW.event = 'codex_unlock' BEGIN SELECT RAISE(ABORT, 'codex unavailable'); END"))
    db_session.commit()
    try:
        with pytest.raises(IntegrityError, match='codex unavailable'):
            settle_session(client, auth_headers, session)
        detail = client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers).json()['session']
        assert detail['status'] == 'active'
        assert detail['return_summary'] is detail['encounter_result'] is None
        assert client.get(f'/api/todos/tasks/{task["id"]}', headers=auth_headers).json()['status'] == 'pending'
        assert client.get('/api/cultivation/overview', headers=auth_headers).json() == before
        assert client.get('/api/cave/events', headers=auth_headers).json() == []
        catalog = client.get('/api/cultivation/retreat/encounters/catalog', headers=auth_headers).json()
        assert all(not event['unlocked'] for event in catalog)
    finally:
        db_session.execute(text('DROP TRIGGER reject_codex'))
        db_session.commit()
    receipt = settle_session(client, auth_headers, session)
    assert receipt['return_summary']['fortune_bonus']['applied'] is True
    assert receipt['return_summary']['first_codex_unlock'] is not None
    events = client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json()
    assert sorted(event['event'] for event in events) == ['codex_unlock', 'retreat_complete']
    assert settle_session(client, auth_headers, session) == receipt
    assert client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json() == events
