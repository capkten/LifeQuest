from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def onboarding_clock(clock, monkeypatch):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]

    def set_time(value):
        instant[0] = value
        clock(value)

    monkeypatch.setattr('app.services.cultivation_retreat.utc_now', lambda: instant[0])
    monkeypatch.setattr('app.services.encounter_engine.random.random', lambda: 1.0)
    set_time(instant[0])
    return set_time


def home(client, headers):
    response = client.get('/api/cave/today', headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('status', ['pending', 'in_progress', 'completed', 'cancelled'])
def test_any_existing_task_excludes_onboarding_even_after_the_task_is_deleted(client, auth_headers, onboarding_clock, status):
    task = client.post('/api/todos/tasks', headers=auth_headers, json={'title': '已经有的一件事'}).json()
    assert client.put(f"/api/todos/tasks/{task['id']}", headers=auth_headers, json={'status': status}).status_code == 200
    assert home(client, auth_headers)['onboarding'] == {'status': 'not_required', 'completed_session_id': None}
    assert client.delete(f"/api/todos/tasks/{task['id']}", headers=auth_headers).status_code == 200
    assert home(client, auth_headers)['onboarding']['status'] == 'not_required'
    assert client.get('/api/cave/events', headers=auth_headers).json() == []


@pytest.mark.parametrize('evidence', ['cave_open', 'active', 'aborted', 'completed'])
def test_genuine_prior_cave_use_excludes_first_run_onboarding(client, auth_headers, onboarding_clock, evidence):
    if evidence == 'cave_open':
        assert client.post('/api/cave/events', headers=auth_headers, json={
            'event': 'cave_open', 'mode': 'morning', 'has_active_session': False, 'request_id': str(uuid4()),
        }).status_code == 200
    else:
        session = client.post('/api/cave/sessions', headers=auth_headers,
                              json={'target_duration': 15, 'request_id': str(uuid4())}).json()
        if evidence != 'active':
            onboarding_clock(datetime(2026, 9, 12, 2, 12, tzinfo=timezone.utc))
            assert client.post(f"/api/cave/sessions/{session['id']}/settle", headers=auth_headers,
                               json={'early': evidence == 'aborted', 'request_id': str(uuid4())}).status_code == 200
    assert home(client, auth_headers)['onboarding'] == {'status': 'not_required', 'completed_session_id': None}
    events = client.get('/api/cave/events', headers=auth_headers).json()
    assert not any(event['event'].startswith('onboarding_') for event in events)


def test_skip_is_terminal_retry_safe_and_grants_no_resources(client, auth_headers, onboarding_clock):
    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    payload = {'request_id': str(uuid4())}
    response = client.post('/api/cave/onboarding/skip', headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {'status': 'skipped', 'completed_session_id': None}
    for request in (payload, {'request_id': str(uuid4())}):
        assert client.post('/api/cave/onboarding/skip', headers=auth_headers, json=request).json() == response.json()
    assert home(client, auth_headers)['onboarding'] == response.json()
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points', 'recent_rewards'):
        assert after[key] == before[key]
    events = client.get('/api/cave/events', headers=auth_headers).json()
    assert sorted(event['event'] for event in events) == ['onboarding_skip', 'onboarding_start']
    assert all(event['source'] == 'onboarding' for event in events)
    assert client.post('/api/cave/events', headers=auth_headers, json={'event': 'onboarding_skip', 'mode': 'day',
        'has_active_session': False, 'request_id': str(uuid4())}).status_code == 422
    assert client.post('/api/cave/onboarding/reset', headers=auth_headers, json=payload).status_code == 404


def test_successful_twelve_actual_minutes_of_fifteen_target_completes_once_without_new_rewards(
    client, auth_headers, onboarding_clock
):
    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    assert client.post('/api/cave/events', headers=auth_headers, json={'event': 'cave_open', 'mode': 'morning',
        'has_active_session': False, 'request_id': str(uuid4())}).status_code == 200
    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    task = client.post('/api/todos/workbench/tasks', headers=auth_headers,
                       json={'title': '读五页书', 'request_id': str(uuid4())}).json()
    session = client.post('/api/cave/sessions', headers=auth_headers, json={
        'target_duration': 15, 'todo_id': task['id'], 'mark_todo_complete': True, 'request_id': str(uuid4()),
    }).json()
    onboarding_clock(datetime(2026, 9, 12, 2, 12, tzinfo=timezone.utc))
    settled = client.post(f"/api/cave/sessions/{session['id']}/settle", headers=auth_headers,
                          json={'request_id': str(uuid4())}).json()
    assert settled['status'] == 'completed' and settled['actual_duration'] == 12
    assert settled['encounter_result']['rarity'] == 'common'
    assert settled['return_summary']['first_codex_unlock'] is not None
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    payload = {'request_id': str(uuid4()), 'session_id': session['id']}
    response = client.post('/api/cave/onboarding/complete', headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {'status': 'completed', 'completed_session_id': session['id']}
    assert home(client, auth_headers)['onboarding'] == response.json()
    for request in (payload, {**payload, 'request_id': str(uuid4())}):
        assert client.post('/api/cave/onboarding/complete', headers=auth_headers, json=request).json() == response.json()
    assert client.post('/api/cave/onboarding/skip', headers=auth_headers, json={'request_id': str(uuid4())}).json() == response.json()
    assert client.post('/api/cave/onboarding/skip', headers=auth_headers, json={'request_id': payload['request_id']}).status_code == 409
    assert client.get(f"/api/cave/sessions/{session['id']}", headers=auth_headers).json()['session'] == settled
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points', 'recent_rewards'):
        assert after[key] == before[key]
    companions = client.get('/api/cave/companions', headers=auth_headers).json()
    assert companions['active_pet_key'] is None
    assert not next(pet for pet in companions['pets'] if pet['key'] == 'white_deer')['unlocked']
    events = client.get('/api/cave/events', headers=auth_headers).json()
    assert [event['event'] for event in events].count('onboarding_start') == 1
    assert [event['event'] for event in events].count('onboarding_complete') == 1
    assert not any(event['event'] == 'onboarding_skip' for event in events)
    complete = next(event for event in events if event['event'] == 'onboarding_complete')
    assert complete['session_id'] == session['id'] and complete['facts'] == {'status': 'completed'}


@pytest.mark.parametrize('kind', ['active', 'aborted', 'wrong_target', 'before_open'])
def test_completion_rejects_sessions_without_eligible_success_after_first_open(
    client, auth_headers, onboarding_clock, db_session, user, kind
):
    from app.models.cultivation_retreat import CultivationRetreat

    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    if kind == 'before_open':
        session = CultivationRetreat(user_id=user.id, target_duration=15, actual_duration=15, status='completed',
            started_at=datetime(2026, 9, 12, 1), ended_at=datetime(2026, 9, 12, 1, 15))
        db_session.add(session)
        db_session.commit()
        session_id = str(session.id)
    else:
        session = client.post('/api/cave/sessions', headers=auth_headers, json={
            'target_duration': 25 if kind == 'wrong_target' else 15, 'request_id': str(uuid4()),
        }).json()
        session_id = session['id']
        if kind != 'active':
            onboarding_clock(datetime(2026, 9, 12, 2, 25, tzinfo=timezone.utc))
            assert client.post(f'/api/cave/sessions/{session_id}/settle', headers=auth_headers,
                json={'early': kind == 'aborted', 'request_id': str(uuid4())}).status_code == 200
    response = client.post('/api/cave/onboarding/complete', headers=auth_headers,
                           json={'request_id': str(uuid4()), 'session_id': session_id})
    assert response.status_code == 409, response.text
    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    assert not any(event['event'] == 'onboarding_complete' for event in client.get('/api/cave/events', headers=auth_headers).json())


def test_onboarding_requires_home_and_owned_session_and_keeps_users_independent(client, auth_headers, onboarding_clock, db_session):
    from app.models.user import User
    from app.services.auth import create_access_token

    assert client.post('/api/cave/onboarding/skip', headers=auth_headers,
                       json={'request_id': str(uuid4())}).status_code == 409
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    db_session.add(other)
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    assert home(client, other_auth)['onboarding']['status'] == 'pending'
    session = client.post('/api/cave/sessions', headers=auth_headers,
                          json={'target_duration': 15, 'request_id': str(uuid4())}).json()
    onboarding_clock(datetime(2026, 9, 12, 2, 12, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{session['id']}/settle", headers=auth_headers,
                       json={'request_id': str(uuid4())}).status_code == 200
    request_id = str(uuid4())
    for session_id in (session['id'], str(uuid4())):
        assert client.post('/api/cave/onboarding/complete', headers=other_auth,
            json={'request_id': request_id, 'session_id': session_id}).status_code == 404
    own = client.post('/api/cave/onboarding/complete', headers=auth_headers,
                     json={'request_id': request_id, 'session_id': session['id']})
    assert own.status_code == 200, own.text
    assert home(client, other_auth)['onboarding']['status'] == 'pending'
    assert client.post('/api/cave/onboarding/skip', headers=other_auth, json={'request_id': request_id}).json()['status'] == 'skipped'
    assert home(client, auth_headers)['onboarding']['status'] == 'completed'
    for field in ({'request_id': str(uuid4())}, {'request_id': str(uuid4()), 'session_id': 'invalid'}):
        assert client.post('/api/cave/onboarding/complete', headers=auth_headers, json=field).status_code == 422


@pytest.mark.parametrize('actions', [('skip', 'complete'), ('complete', 'complete')])
def test_concurrent_first_home_and_terminal_requests_emit_each_transition_once(
    client, auth_headers, onboarding_clock, database, user, monkeypatch, actions
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker
    from app.database import get_db
    from app.main import app
    from app.models.user import User

    database.add(User(id=user.id, username='onboarding-race', email='onboarding-race@example.com', password_hash='unused'))
    database.commit()
    sessions = sessionmaker(bind=database.get_bind())

    def get_file_db():
        with sessions() as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, get_file_db)

    def together(operation, values):
        barrier = Barrier(2)

        def invoke(value):
            barrier.wait(timeout=10)
            return operation(value)

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(invoke, values))

    first = together(lambda _: home(client, auth_headers)['onboarding'], [0, 1])
    assert first == [{'status': 'pending', 'completed_session_id': None}] * 2
    session = client.post('/api/cave/sessions', headers=auth_headers,
                          json={'target_duration': 15, 'request_id': str(uuid4())}).json()
    onboarding_clock(datetime(2026, 9, 12, 2, 12, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{session['id']}/settle", headers=auth_headers,
                       json={'request_id': str(uuid4())}).status_code == 200

    def terminal(action):
        payload = {'request_id': str(uuid4())}
        if action == 'complete':
            payload['session_id'] = session['id']
        response = client.post(f'/api/cave/onboarding/{action}', headers=auth_headers, json=payload)
        assert response.status_code == 200, response.text
        return response.json()

    results = together(terminal, actions)
    assert results[0] == results[1]
    assert results[0]['status'] in ('skipped', 'completed')
    assert home(client, auth_headers)['onboarding'] == results[0]
    events = client.get('/api/cave/events', headers=auth_headers).json()
    names = [event['event'] for event in events if event['source'] == 'onboarding']
    assert names.count('onboarding_start') == 1
    assert names.count('onboarding_skip') + names.count('onboarding_complete') == 1


def test_failed_completion_rolls_back_state_and_telemetry_then_retries_same_request(
    client, auth_headers, onboarding_clock, db_session
):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    assert home(client, auth_headers)['onboarding']['status'] == 'pending'
    session = client.post('/api/cave/sessions', headers=auth_headers,
                          json={'target_duration': 15, 'request_id': str(uuid4())}).json()
    onboarding_clock(datetime(2026, 9, 12, 2, 12, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{session['id']}/settle", headers=auth_headers,
                       json={'request_id': str(uuid4())}).status_code == 200
    db_session.execute(text("CREATE TRIGGER fail_onboarding_complete BEFORE INSERT ON cave_requests "
                            "WHEN NEW.operation = 'onboarding_complete' BEGIN SELECT RAISE(ABORT, 'onboarding write failed'); END"))
    db_session.commit()
    payload = {'request_id': str(uuid4()), 'session_id': session['id']}
    with pytest.raises(IntegrityError, match='onboarding write failed'):
        client.post('/api/cave/onboarding/complete', headers=auth_headers, json=payload)
    assert home(client, auth_headers)['onboarding'] == {'status': 'pending', 'completed_session_id': None}
    events = client.get('/api/cave/events', headers=auth_headers).json()
    assert not any(event['event'] == 'onboarding_complete' for event in events)
    db_session.execute(text('DROP TRIGGER fail_onboarding_complete'))
    db_session.commit()
    response = client.post('/api/cave/onboarding/complete', headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json() == {'status': 'completed', 'completed_session_id': session['id']}
    events = client.get('/api/cave/events', headers=auth_headers).json()
    assert sum(event['event'] == 'onboarding_complete' for event in events) == 1


def test_first_home_with_no_tasks_is_pending_despite_prior_growth_and_companion_reads(client, auth_headers, onboarding_clock):
    for path in ('growth', 'companions', 'codex'):
        assert client.get(f'/api/cave/{path}', headers=auth_headers).status_code == 200
    first = home(client, auth_headers)
    assert first['onboarding'] == {'status': 'pending', 'completed_session_id': None}
    assert first['signs'] == []
    assert home(client, auth_headers)['onboarding'] == first['onboarding']
    events = client.get('/api/cave/events', headers=auth_headers).json()
    assert [event['event'] for event in events] == ['onboarding_start']
    assert events[0]['source'] == 'onboarding'
    assert events[0]['facts'] == {'status': 'pending'}
