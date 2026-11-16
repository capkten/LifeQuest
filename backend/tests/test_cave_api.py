from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.user import User
from app.services.auth import create_access_token


def create_task(client, auth, **values):
    status = values.pop('status', None)
    response = client.post('/api/todos/tasks', headers=auth, json={'title': '眼前的事', **values})
    assert response.status_code == 200
    if status:
        response = client.put(f'/api/todos/tasks/{response.json()["id"]}', headers=auth, json={'status': status})
        assert response.status_code == 200
    return response.json()


def test_primary_sign_uses_workbench_order_and_excludes_closed_or_foreign_tasks(client, auth_headers, clock):
    auth = auth_headers
    upcoming = create_task(client, auth, title='稍后', deadline='2026-09-20T10:00:00Z')
    high = create_task(client, auth, title='重要', priority='high')
    active = create_task(client, auth, title='继续', status='in_progress')
    due = create_task(client, auth, title='今天', deadline='2026-09-12T10:00:00Z')
    overdue = create_task(client, auth, title='先做', deadline='2026-09-11T10:00:00Z')
    create_task(client, auth, title='已取消', status='cancelled', deadline='2026-01-01T10:00:00Z')
    for task in [overdue, due, active, high, upcoming]:
        cave = client.get('/api/cave/today', headers=auth).json()
        assert cave['primary_sign']['id'] == task['id']
        assert cave['summary'] == client.get('/api/todos/workbench', headers=auth).json()['summary']
        assert client.post(f'/api/todos/tasks/{task["id"]}/complete', headers=auth).status_code == 200
    assert client.get('/api/cave/today', headers=auth).json()['primary_sign'] is None


def test_today_primary_sign_prefers_high_priority_over_an_earlier_deadline(client, auth_headers, clock):
    create_task(client, auth_headers, title='早些到期的小事', priority='low', deadline='2026-09-12T01:00:00Z')
    important = create_task(client, auth_headers, title='今天重要的事', priority='high', deadline='2026-09-12T10:00:00Z')
    response = client.get('/api/cave/today', headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['primary_sign']['id'] == important['id']


def test_cave_china_midnight_refreshes_the_date_and_day_groups(client, auth_headers, clock):
    clock(datetime(2026, 9, 12, 15, 59, tzinfo=timezone.utc))
    task = create_task(client, auth_headers, deadline='2026-09-12T15:59:59Z')
    before = client.get('/api/cave/today', headers=auth_headers).json()
    assert before['date'] == '2026-09-12'
    assert before['primary_sign']['source'] == '今天到期'
    clock(datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc))
    after = client.get('/api/cave/today', headers=auth_headers).json()
    assert after['date'] == '2026-09-13'
    assert after['primary_sign']['id'] == task['id']
    assert after['primary_sign']['source'] == '逾期'
    assert after['fortune'] == client.get('/api/cave/today', headers=auth_headers).json()['fortune']


def test_cave_isolates_tasks_and_sessions_and_rejects_foreign_binding(client, db_session, auth_headers, clock):
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    db_session.add(other)
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    task = create_task(client, other_auth, deadline='2026-01-01T10:00:00Z')
    payload = {'target_duration': 15, 'todo_id': task['id'], 'request_id': str(uuid4())}
    assert client.post('/api/cave/sessions', headers=other_auth, json=payload).status_code == 200
    own = client.get('/api/cave/today', headers=auth_headers).json()
    assert own['primary_sign'] is None
    assert own['active_session'] is None
    assert own['first_session'] is True
    assert client.post('/api/cave/signs/select', headers=auth_headers,
                       json={'date': '2026-09-12', 'task_id': task['id'], 'request_id': str(uuid4())}).status_code == 404
    assert client.post('/api/cave/sessions', headers=auth_headers, json=payload).status_code == 404
    assert client.get('/api/cave/today').status_code == 401
    client.delete(f'/api/todos/tasks/{task["id"]}', headers=other_auth)
    assert client.get('/api/cave/today', headers=other_auth).json()['primary_sign'] is None


def test_three_signs_persist_order_and_replenish_after_primary_completion(client, auth_headers, clock):
    tasks = [create_task(client, auth_headers, title=f'第{index}件事', deadline=f'2026-09-{day:02d}T10:00:00Z')
             for index, day in enumerate([9, 10, 11, 12], start=1)]
    first = client.get('/api/cave/today', headers=auth_headers).json()
    assert [task['id'] for task in first['signs']] == [task['id'] for task in tasks[:3]]
    assert first['reroll_used'] is False
    client.post(f'/api/todos/tasks/{tasks[0]["id"]}/complete', headers=auth_headers)
    refreshed = client.get('/api/cave/today', headers=auth_headers).json()
    assert [task['id'] for task in refreshed['signs']] == [task['id'] for task in tasks[1:]]
    assert refreshed['fortune'] == first['fortune']
    assert refreshed['all_signs_done'] is False
    for task in tasks[1:]:
        client.post(f'/api/todos/tasks/{task["id"]}/complete', headers=auth_headers)
    finished = client.get('/api/cave/today', headers=auth_headers).json()
    assert finished['signs'] == []
    assert finished['all_signs_done'] is True


def test_daily_reroll_only_changes_primary_and_replays_without_spending_twice(client, auth_headers, clock):
    tasks = [create_task(client, auth_headers, title=f'签{index}', deadline=f'2026-09-{day:02d}T10:00:00Z')
             for index, day in enumerate([9, 10, 11, 12], start=1)]
    original = client.get('/api/cave/today', headers=auth_headers).json()
    payload = {'date': original['date'], 'request_id': str(uuid4())}
    changed = client.post('/api/cave/signs/reroll', headers=auth_headers, json=payload)
    assert changed.status_code == 200
    assert [task['id'] for task in changed.json()['signs']] == [tasks[3]['id'], tasks[1]['id'], tasks[2]['id']]
    assert changed.json()['reroll_used'] is True
    assert client.post('/api/cave/signs/reroll', headers=auth_headers, json=payload).json() == changed.json()
    second = client.post('/api/cave/signs/reroll', headers=auth_headers, json={**payload, 'request_id': str(uuid4())})
    assert second.status_code == 409
    assert second.json()['detail'] == '今日已换签'
    assert client.get('/api/cave/today', headers=auth_headers).json()['primary_sign']['id'] == tasks[3]['id']


def test_selecting_backup_or_unscheduled_bucket_task_is_free_and_persists(client, auth_headers, clock):
    tasks = [create_task(client, auth_headers, title=f'签{index}', deadline=f'2026-09-{day:02d}T10:00:00Z')
             for index, day in enumerate([9, 10, 11], start=1)]
    ordinary = create_task(client, auth_headers, title='不排期也可以选', priority='low')
    first = client.get('/api/cave/today', headers=auth_headers).json()
    payload = {'date': first['date'], 'task_id': tasks[2]['id'], 'request_id': str(uuid4())}
    selected = client.post('/api/cave/signs/select', headers=auth_headers, json=payload)
    assert selected.status_code == 200
    assert [task['id'] for task in selected.json()['signs']] == [tasks[2]['id'], tasks[0]['id'], tasks[1]['id']]
    assert selected.json()['reroll_used'] is False
    assert client.post('/api/cave/signs/select', headers=auth_headers, json=payload).json() == selected.json()
    selected = client.post('/api/cave/signs/select', headers=auth_headers,
                           json={**payload, 'task_id': ordinary['id'], 'request_id': str(uuid4())})
    assert selected.status_code == 200
    assert [task['id'] for task in selected.json()['signs']] == [ordinary['id'], tasks[2]['id'], tasks[0]['id']]
    persisted = client.get('/api/cave/today', headers=auth_headers).json()
    assert persisted['primary_sign']['id'] == ordinary['id']
    assert persisted['reroll_used'] is False


def test_daily_signs_reset_at_china_midnight_and_reject_stale_new_mutations(client, auth_headers, clock):
    tasks = [create_task(client, auth_headers, title=f'签{index}', deadline=f'2026-09-{day:02d}T10:00:00Z')
             for index, day in enumerate([9, 10, 11, 12], start=1)]
    original = client.get('/api/cave/today', headers=auth_headers).json()
    payload = {'date': original['date'], 'request_id': str(uuid4())}
    previous = client.post('/api/cave/signs/reroll', headers=auth_headers, json=payload).json()
    clock(datetime(2026, 9, 12, 16, tzinfo=timezone.utc))
    next_day = client.get('/api/cave/today', headers=auth_headers).json()
    assert next_day['date'] == '2026-09-13'
    assert next_day['reroll_used'] is False
    assert next_day['primary_sign']['id'] == tasks[0]['id']
    assert client.post('/api/cave/signs/reroll', headers=auth_headers, json=payload).json() == previous
    stale = {**payload, 'request_id': str(uuid4())}
    assert client.post('/api/cave/signs/reroll', headers=auth_headers, json=stale).status_code == 409
    assert client.post('/api/cave/signs/select', headers=auth_headers, json={**stale, 'task_id': tasks[2]['id']}).status_code == 409
    assert client.get('/api/cave/today', headers=auth_headers).json()['primary_sign']['id'] == tasks[0]['id']


def test_select_rejects_unavailable_tasks_and_reused_request_with_different_content(client, auth_headers, clock):
    first = create_task(client, auth_headers, deadline='2026-09-12T10:00:00Z')
    second = create_task(client, auth_headers, deadline='2026-09-12T11:00:00Z')
    payload = {'date': '2026-09-12', 'task_id': first['id'], 'request_id': str(uuid4())}
    assert client.post('/api/cave/signs/select', headers=auth_headers, json=payload).status_code == 200
    assert client.post('/api/cave/signs/select', headers=auth_headers, json={**payload, 'task_id': second['id']}).status_code == 409
    assert client.post('/api/cave/signs/reroll', headers=auth_headers,
                       json={'date': payload['date'], 'request_id': payload['request_id']}).status_code == 409
    client.post(f'/api/todos/tasks/{second["id"]}/complete', headers=auth_headers)
    unavailable = {**payload, 'task_id': second['id'], 'request_id': str(uuid4())}
    assert client.post('/api/cave/signs/select', headers=auth_headers, json=unavailable).status_code == 404
    unavailable['task_id'] = str(uuid4())
    assert client.post('/api/cave/signs/select', headers=auth_headers, json=unavailable).status_code == 404


def test_reroll_without_an_alternative_keeps_the_free_change(client, auth_headers, clock):
    create_task(client, auth_headers, deadline='2026-09-12T10:00:00Z')
    payload = {'date': '2026-09-12', 'request_id': str(uuid4())}
    assert client.post('/api/cave/signs/reroll', headers=auth_headers, json=payload).status_code == 409
    assert client.get('/api/cave/today', headers=auth_headers).json()['reroll_used'] is False


def test_cave_start_reuses_active_session_and_replays_request_after_session_ends(client, auth_headers, clock):
    task = create_task(client, auth_headers)
    payload = {'target_duration': 15, 'todo_id': task['id'], 'request_id': str(uuid4())}
    first = client.post('/api/cave/sessions', headers=auth_headers, json=payload)
    assert first.status_code == 200
    session = first.json()
    assert session['todo_id'] == task['id']
    assert session['rule_version'] == 'b_v1'
    again = client.post('/api/cave/sessions', headers=auth_headers, json={**payload, 'request_id': str(uuid4())})
    assert again.json()['id'] == session['id']
    assert client.get('/api/cave/today', headers=auth_headers).json()['active_session']['id'] == session['id']
    assert client.post(f'/api/cultivation/retreat/{session["id"]}/abort', headers=auth_headers).status_code == 200
    replay = client.post('/api/cave/sessions', headers=auth_headers, json=payload)
    assert replay.json() == session
    assert client.get('/api/cave/today', headers=auth_headers).json()['active_session'] is None


def test_session_start_persists_the_planned_task_choice_and_title(client, auth_headers):
    task = create_task(client, auth_headers, title='读完这一章')
    response = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 90, 'todo_id': task['id'], 'mark_todo_complete': False,
        'request_id': str(uuid4()),
    })
    assert response.status_code == 200, response.text
    session = response.json()
    assert session['mark_todo_complete'] is False
    assert session['todo_title'] == '读完这一章'
    restored = client.get('/api/cave/today', headers=auth_headers).json()['active_session']
    assert restored == session


def test_session_deep_link_restores_only_the_owners_session_with_server_time(client, auth_headers, db_session):
    session = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 15, 'request_id': str(uuid4()),
    }).json()
    response = client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers)
    assert response.status_code == 200, response.text
    assert response.json()['session'] == session
    assert response.json()['session']['mark_todo_complete'] is True
    assert datetime.fromisoformat(response.json()['server_now']).tzinfo is not None
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    db_session.add(other)
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    assert client.get(f'/api/cave/sessions/{session["id"]}', headers=other_auth).status_code == 404
    assert client.post(f'/api/cave/sessions/{session["id"]}/settle', headers=other_auth,
                       json={'request_id': str(uuid4()), 'early': True}).status_code == 404
    assert client.get(f'/api/cave/sessions/{uuid4()}', headers=auth_headers).status_code == 404


@pytest.mark.parametrize('mark_complete,exp', [(True, 6), (False, 3)])
def test_session_settles_at_eighty_percent_using_the_saved_task_choice(
    client, auth_headers, monkeypatch, mark_complete, exp,
):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]
    monkeypatch.setattr('app.services.cultivation_retreat.utc_now', lambda: instant[0])
    task = create_task(client, auth_headers)
    session = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 15, 'todo_id': task['id'], 'mark_todo_complete': mark_complete,
        'request_id': str(uuid4()),
    }).json()
    instant[0] = datetime(2026, 9, 12, 2, 12, tzinfo=timezone.utc)
    response = client.post(f'/api/cave/sessions/{session["id"]}/settle', headers=auth_headers,
                           json={'request_id': str(uuid4()), 'early': False})
    assert response.status_code == 200, response.text
    settled = response.json()
    assert settled['status'] == 'completed'
    assert (settled['qi_gained'], settled['exp_gained']) == (12, exp)
    assert settled['settlement_result']['task_completed'] is mark_complete
    assert client.get(f'/api/todos/tasks/{task["id"]}', headers=auth_headers).json()['status'] == ('completed' if mark_complete else 'pending')
    assert client.get('/api/cave/today', headers=auth_headers).json()['active_session'] is None


def test_collect_before_eighty_percent_keeps_session_active_but_explicit_early_end_never_completes_task(
    client, auth_headers, monkeypatch,
):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]
    monkeypatch.setattr('app.services.cultivation_retreat.utc_now', lambda: instant[0])
    task = create_task(client, auth_headers)
    session = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 25, 'todo_id': task['id'], 'request_id': str(uuid4()),
    }).json()
    instant[0] = datetime(2026, 9, 12, 2, 19, 59, tzinfo=timezone.utc)
    endpoint = f'/api/cave/sessions/{session["id"]}/settle'
    response = client.post(endpoint, headers=auth_headers, json={'request_id': str(uuid4())})
    assert response.status_code == 409, response.text
    assert client.get('/api/cave/today', headers=auth_headers).json()['active_session']['id'] == session['id']
    instant[0] = datetime(2026, 9, 12, 2, 21, tzinfo=timezone.utc)
    response = client.post(endpoint, headers=auth_headers, json={'request_id': str(uuid4()), 'early': True})
    assert response.status_code == 200, response.text
    assert (response.json()['status'], response.json()['qi_gained'], response.json()['exp_gained']) == ('aborted', 21, 5)
    assert response.json()['settlement_result']['task_reward'] is None
    assert client.get(f'/api/todos/tasks/{task["id"]}', headers=auth_headers).json()['status'] == 'pending'


@pytest.mark.parametrize('status', ['completed', 'cancelled'])
def test_new_session_binding_requires_a_currently_incomplete_task(client, auth_headers, status):
    task = create_task(client, auth_headers)
    if status == 'completed':
        client.post(f'/api/todos/tasks/{task["id"]}/complete', headers=auth_headers)
    else:
        client.put(f'/api/todos/tasks/{task["id"]}', headers=auth_headers, json={'status': status})
    response = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 15, 'todo_id': task['id'], 'request_id': str(uuid4()),
    })
    assert response.status_code == 409, response.text
    assert client.get('/api/cave/today', headers=auth_headers).json()['active_session'] is None


def test_cave_settlement_replays_the_same_receipt_across_requests_and_legacy_endpoints(client, auth_headers):
    session = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 15, 'request_id': str(uuid4()),
    }).json()
    endpoint = f'/api/cave/sessions/{session["id"]}/settle'
    payload = {'request_id': str(uuid4()), 'early': True}
    first = client.post(endpoint, headers=auth_headers, json=payload)
    assert first.status_code == 200, first.text
    receipt = first.json()
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    assert (receipt['qi_gained'], receipt['exp_gained'], receipt['coins_gained']) == (0, 0, 0)
    assert client.post(endpoint, headers=auth_headers, json=payload).json() == receipt
    assert client.post(endpoint, headers=auth_headers, json={**payload, 'early': False}).status_code == 409
    assert client.post(endpoint, headers=auth_headers, json={'request_id': str(uuid4()), 'early': False}).json() == receipt
    for action in ('complete', 'abort'):
        assert client.post(f'/api/cultivation/retreat/{session["id"]}/{action}', headers=auth_headers).json() == receipt
    assert client.get(f'/api/cave/sessions/{session["id"]}', headers=auth_headers).json()['session'] == receipt
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for resource in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'recent_rewards'):
        assert after[resource] == before[resource]


def test_notification_click_records_owned_session_facts_once_without_settling(client, auth_headers):
    response = client.post('/api/cave/sessions', headers=auth_headers,
                           json={'target_duration': 25, 'request_id': str(uuid4())})
    assert response.status_code == 200, response.text
    session = response.json()
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for notification_type, delay in [('ongoing', 0), ('completion', 172800000), ('finish', 9007199254740991)]:
        payload = {'event': 'notification_click', 'session_id': session['id'],
                   'notification_type': notification_type, 'delay_ms': delay,
                   'source': 'notification', 'mode': 'night', 'has_active_session': False,
                   'request_id': str(uuid4()), 'facts': {'session_status': 'completed'}}
        response = client.post('/api/cave/events', headers=auth_headers, json=payload)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['facts'] == {'notification_type': notification_type, 'delay_ms': delay, 'session_status': 'active'}
        assert client.post('/api/cave/events', headers=auth_headers, json=payload).json() == result
        assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'delay_ms': 1}).status_code == 409
    events = client.get('/api/cave/events', headers=auth_headers, params={'session_id': session['id']}).json()
    assert len(events) == 3
    assert {(event['facts']['notification_type'], event['facts']['delay_ms']) for event in events} == {
        ('ongoing', 0), ('completion', 172800000), ('finish', 9007199254740991)}
    assert all(event['facts']['session_status'] == 'active' for event in events)
    current = client.get(f"/api/cave/sessions/{session['id']}", headers=auth_headers).json()['session']
    assert current == session
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points', 'recent_rewards'):
        assert after[key] == before[key]


def test_notification_click_requires_session_type_and_safe_integer_delay(client, auth_headers):
    session = client.post('/api/cave/sessions', headers=auth_headers,
                          json={'target_duration': 25, 'request_id': str(uuid4())}).json()
    payload = {'event': 'notification_click', 'session_id': session['id'], 'notification_type': 'ongoing',
               'delay_ms': 0, 'mode': 'night', 'has_active_session': True, 'request_id': str(uuid4())}
    for field in ('session_id', 'notification_type', 'delay_ms', 'mode', 'has_active_session'):
        missing = {key: value for key, value in payload.items() if key != field}
        assert client.post('/api/cave/events', headers=auth_headers, json=missing).status_code == 422
    for field, value in [('session_id', None), ('notification_type', None), ('notification_type', 'unknown'),
                         ('delay_ms', None), ('delay_ms', -1), ('delay_ms', 9007199254740992),
                         ('delay_ms', 1.5), ('delay_ms', '1'), ('delay_ms', True), ('mode', 'unknown')]:
        assert client.post('/api/cave/events', headers=auth_headers, json={**payload, field: value}).status_code == 422
    assert client.get('/api/cave/events', headers=auth_headers).json() == []


def test_notification_click_is_owner_scoped_and_replays_its_original_session_status(client, auth_headers, db_session):
    session = client.post('/api/cave/sessions', headers=auth_headers,
                          json={'target_duration': 25, 'request_id': str(uuid4())}).json()
    payload = {'event': 'notification_click', 'session_id': session['id'], 'notification_type': 'finish',
               'delay_ms': 12, 'source': 'notification', 'mode': 'night', 'has_active_session': True,
               'request_id': str(uuid4())}
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    db_session.add(other)
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    assert client.post('/api/cave/events', headers=other_auth, json=payload).status_code == 404
    assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'session_id': str(uuid4())}).status_code == 404
    assert client.get('/api/cave/events', headers=other_auth).json() == []
    recorded = client.post('/api/cave/events', headers=auth_headers, json=payload).json()
    assert recorded['facts']['session_status'] == 'active'
    settled = client.post(f"/api/cave/sessions/{session['id']}/settle", headers=auth_headers,
                          json={'early': True, 'request_id': str(uuid4())})
    assert settled.status_code == 200, settled.text
    assert client.post('/api/cave/events', headers=auth_headers, json=payload).json() == recorded
    assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'notification_type': 'ongoing'}).status_code == 409
    assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'event': 'return_view'}).status_code == 409
    fresh = client.post('/api/cave/events', headers=auth_headers, json={**payload, 'request_id': str(uuid4())}).json()
    assert fresh['facts']['session_status'] == 'aborted'
    assert client.get(f"/api/cave/sessions/{session['id']}", headers=auth_headers).json()['session'] == settled.json()
    assert client.get('/api/cave/today', headers=auth_headers).json()['pending_return']['session_id'] == session['id']


def test_cave_open_event_records_mode_source_and_active_state_once(client, auth_headers):
    payload = {'event': 'cave_open', 'source': 'direct', 'mode': 'night', 'has_active_session': False, 'request_id': str(uuid4())}
    first = client.post('/api/cave/events', headers=auth_headers, json=payload)
    assert first.status_code == 200
    assert first.json()['event'] == 'cave_open'
    assert first.json()['mode'] == 'night'
    assert client.post('/api/cave/events', headers=auth_headers, json=payload).json() == first.json()
    assert client.post('/api/cave/events', headers=auth_headers, json={**payload, 'event': 'unknown'}).status_code == 422


def test_cave_opens_with_a_stable_daily_fortune_and_empty_action(client, auth_headers, clock):
    first = client.get('/api/cave/today', headers=auth_headers)
    assert first.status_code == 200
    body = first.json()
    assert body['date'] == '2026-09-12'
    assert body['primary_sign'] is None
    assert body['active_session'] is None
    assert body['first_session'] is True
    assert body['fortune']['multiplier'] == 1.1
    assert client.get('/api/cave/today', headers=auth_headers).json()['fortune'] == body['fortune']
