from datetime import datetime, timezone
from uuid import uuid4

import pytest


@pytest.fixture
def letter_clock(clock, monkeypatch, db_session, user):
    instant = [datetime(2026, 9, 6, 15, 59, tzinfo=timezone.utc)]
    user.created_at = datetime(2026, 9, 1, 15, 30)
    db_session.commit()

    def set_time(value):
        instant[0] = value
        clock(value)

    monkeypatch.setattr('app.services.cultivation_retreat.utc_now', lambda: instant[0])
    set_time(instant[0])
    return set_time


def letters(client, headers):
    response = client.get('/api/cave/letters', headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_senior_letters_recur_at_china_monday_eight_without_duplicate_first_letters(client, auth_headers, letter_clock):
    letter_clock(datetime(2026, 9, 6, 16, tzinfo=timezone.utc))
    first = letters(client, auth_headers)['letters'][0]
    letter_clock(datetime(2026, 9, 13, 15, 59, tzinfo=timezone.utc))
    assert letters(client, auth_headers)['letters'] == [first]
    letter_clock(datetime(2026, 9, 13, 16, tzinfo=timezone.utc))
    midnight = letters(client, auth_headers)['letters']
    assert len(midnight) == 2
    brother = next(row for row in midnight if row['senior_key'] == 'lifeng')
    assert brother['senior_name'] == '师兄·砺锋' and brother['week_start'] == '2026-09-14'
    letter_clock(datetime(2026, 9, 13, 23, 59, tzinfo=timezone.utc))
    assert letters(client, auth_headers)['letters'] == midnight
    letter_clock(datetime(2026, 9, 14, 0, tzinfo=timezone.utc))
    monday = letters(client, auth_headers)['letters']
    assert len(monday) == 3
    assert next(row for row in monday if row['id'] == brother['id']) == brother
    letter_clock(datetime(2026, 9, 20, 23, 59, tzinfo=timezone.utc))
    assert [row['id'] for row in letters(client, auth_headers)['letters']] == [row['id'] for row in monday]
    letter_clock(datetime(2026, 9, 21, 0, tzinfo=timezone.utc))
    latest = letters(client, auth_headers)
    assert len(latest['letters']) == 5
    assert [row['senior_key'] for row in latest['letters'] if row['week_start'] == '2026-09-21'] == ['lifeng', 'qingheng']
    assert letters(client, auth_headers) == latest


def test_letter_personalization_freezes_user_week_facts_and_distinct_voices(
    client, auth_headers, letter_clock, db_session, user
):
    from app.models.todo import Task, Habit
    from app.models.cultivation_retreat import CultivationRetreat

    letter_clock(datetime(2026, 9, 15, 0, tzinfo=timezone.utc))
    db_session.add_all([
        Task(user_id=user.id, title='晨间一件', status='completed', completed_at=datetime(2026, 9, 13, 23)),
        Task(user_id=user.id, title='晚间一件', status='completed', completed_at=datetime(2026, 9, 14, 15, 40)),
        Task(user_id=user.id, title='上周一件', status='completed', completed_at=datetime(2026, 9, 13, 15, 40)),
        Task(user_id=uuid4(), title='别人的一件', status='completed', completed_at=datetime(2026, 9, 14, 15, 59)),
        Habit(user_id=user.id, title='自己的习惯', best_streak=7),
        Habit(user_id=uuid4(), title='别人的习惯', best_streak=99),
    ])
    for status, ended in [('completed', datetime(2026, 9, 14, 2)), ('completed', datetime(2026, 9, 14, 4)),
                          ('aborted', datetime(2026, 9, 14, 6)), ('completed', datetime(2026, 9, 12, 2))]:
        db_session.add(CultivationRetreat(user_id=user.id, target_duration=25, actual_duration=25,
                                         status=status, started_at=ended, ended_at=ended))
    db_session.commit()
    initial = letters(client, auth_headers)
    assert len(initial['letters']) == 2  # No missed-week backlog is manufactured.
    for letter in initial['letters']:
        assert letter['variables'] == {'completed_tasks': 2, 'best_streak': 7, 'latest_completion_time': '23:40', 'weekly_sessions': 2}
        assert all(value in letter['body'] for value in ('2 件', '7 天', '23:40', '2 次'))
    sister, brother = ({row['senior_key']: row for row in initial['letters']}[key] for key in ('qingheng', 'lifeng'))
    assert '慢慢来' in sister['body'] and '选定一件' in brother['body']
    db_session.add(Task(user_id=user.id, title='后来的事', status='completed', completed_at=datetime(2026, 9, 14, 15, 45)))
    db_session.commit()
    assert letters(client, auth_headers) == initial


def test_opening_letter_detail_is_read_only_and_explicit_read_is_retry_safe(client, auth_headers, letter_clock):
    letter_clock(datetime(2026, 9, 6, 16, tzinfo=timezone.utc))
    original = letters(client, auth_headers)['letters'][0]
    path = f"/api/cave/letters/{original['id']}"
    detail = client.get(path, headers=auth_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json() == original
    assert letters(client, auth_headers)['unread_count'] == 1
    payload = {'request_id': str(uuid4())}
    response = client.post(f'{path}/read', headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    marked = response.json()
    assert marked['unread_count'] == 0 and marked['letters'][0]['status'] == 'read'
    assert marked['letters'][0]['read_at'] is not None
    letter_clock(datetime(2026, 9, 6, 17, tzinfo=timezone.utc))
    assert client.post(f'{path}/read', headers=auth_headers, json=payload).json() == marked
    assert client.get(path, headers=auth_headers).json() == marked['letters'][0]
    assert client.post(f'{path}/read', headers=auth_headers, json={'request_id': str(uuid4())}).json() == marked


def test_only_one_trial_can_be_accepted_per_china_week_with_stable_retry(client, auth_headers, letter_clock):
    letter_clock(datetime(2026, 9, 14, 0, tzinfo=timezone.utc))
    inbox = letters(client, auth_headers)
    sister, brother = ({row['senior_key']: row for row in inbox['letters']}[key] for key in ('qingheng', 'lifeng'))
    assert sister['trial']['can_accept'] is True and brother['trial']['can_accept'] is True
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    payload = {'request_id': str(uuid4())}
    path = f"/api/cave/letters/{sister['id']}/accept"
    response = client.post(path, headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    accepted = response.json()
    assert accepted['accepted_trial'] == {'letter_id': sister['id'], 'week_start': '2026-09-14', 'status': 'accepted'}
    selected = next(row for row in accepted['letters'] if row['id'] == sister['id'])
    assert selected['status'] == 'accepted' and selected['trial']['status'] == 'accepted'
    assert not any(row['trial']['can_accept'] for row in accepted['letters'])
    assert client.post(f"/api/cave/letters/{brother['id']}/accept", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    assert client.post(path, headers=auth_headers, json=payload).json() == accepted
    assert client.post(path, headers=auth_headers, json={'request_id': str(uuid4())}).json() == accepted
    assert client.post(f"/api/cave/letters/{sister['id']}/read", headers=auth_headers, json=payload).status_code == 409
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points'):
        assert after[key] == before[key]
    letter_clock(datetime(2026, 9, 21, 0, tzinfo=timezone.utc))
    next_week = letters(client, auth_headers)
    assert next_week['accepted_trial'] is None
    assert not next(row for row in next_week['letters'] if row['id'] == brother['id'])['trial']['can_accept']
    assert client.post(f"/api/cave/letters/{brother['id']}/accept", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    new_letter = next(row for row in next_week['letters'] if row['week_start'] == '2026-09-21')
    assert client.post(f"/api/cave/letters/{new_letter['id']}/accept", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200


def test_declining_has_no_penalty_does_not_spend_the_trial_and_next_week_changes_it(client, auth_headers, letter_clock):
    letter_clock(datetime(2026, 9, 14, 0, tzinfo=timezone.utc))
    inbox = letters(client, auth_headers)
    sister, brother = ({row['senior_key']: row for row in inbox['letters']}[key] for key in ('qingheng', 'lifeng'))
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    payload = {'request_id': str(uuid4())}
    path = f"/api/cave/letters/{sister['id']}/decline"
    response = client.post(path, headers=auth_headers, json=payload)
    assert response.status_code == 200, response.text
    declined = response.json()
    selected = next(row for row in declined['letters'] if row['id'] == sister['id'])
    assert selected['status'] == 'declined' and selected['trial']['status'] == 'declined'
    assert selected['trial']['can_accept'] is False
    assert declined['accepted_trial'] is None
    assert next(row for row in declined['letters'] if row['id'] == brother['id'])['trial']['can_accept'] is True
    assert client.post(f"/api/cave/letters/{sister['id']}/accept", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    assert client.post(f"/api/cave/letters/{brother['id']}/accept", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert client.post(f"/api/cave/letters/{brother['id']}/decline", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    assert client.post(path, headers=auth_headers, json=payload).json() == declined
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points'):
        assert after[key] == before[key]
    letter_clock(datetime(2026, 9, 21, 0, tzinfo=timezone.utc))
    following = next(row for row in letters(client, auth_headers)['letters'] if row['senior_key'] == 'qingheng' and row['week_start'] == '2026-09-21')
    assert following['trial']['key'] != sister['trial']['key']
    assert following['trial']['can_accept'] is True


def test_night_trial_uses_new_persisted_sessions_and_claims_one_story_without_resources(
    client, auth_headers, letter_clock, db_session, user
):
    from app.models.cultivation_retreat import CultivationRetreat

    letter_clock(datetime(2026, 9, 7, 14, tzinfo=timezone.utc))
    db_session.add(CultivationRetreat(user_id=user.id, target_duration=25, actual_duration=25,
        status='completed', started_at=datetime(2026, 9, 7, 13), ended_at=datetime(2026, 9, 7, 13, 25)))
    db_session.commit()
    original = letters(client, auth_headers)['letters'][0]
    assert original['trial']['key'] == 'quiet_night'
    path = f"/api/cave/letters/{original['id']}"
    claim = lambda payload: client.post(f'{path}/claim', headers=auth_headers, json=payload)
    assert claim({'request_id': str(uuid4())}).status_code == 409
    accepted = client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())})
    assert accepted.status_code == 200
    assert claim({'request_id': str(uuid4()), 'current': 999}).status_code == 409
    started = client.post('/api/cave/sessions', headers=auth_headers, json={'request_id': str(uuid4()), 'target_duration': 25}).json()
    letter_clock(datetime(2026, 9, 7, 14, 24, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert claim({'request_id': str(uuid4())}).status_code == 409  # 80% completion is not 25 actual minutes.
    started = client.post('/api/cave/sessions', headers=auth_headers, json={'request_id': str(uuid4()), 'target_duration': 25}).json()
    letter_clock(datetime(2026, 9, 7, 14, 49, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    ready = client.get(path, headers=auth_headers).json()
    assert ready['trial']['status'] == 'ready' and ready['trial']['current'] == 1
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    payload = {'request_id': str(uuid4())}
    response = claim(payload)
    assert response.status_code == 200, response.text
    result = response.json()
    finished = result['letters'][0]
    assert finished['status'] == 'completed' and finished['trial']['status'] == 'completed'
    assert finished['body'] == original['body'] and finished['variables'] == original['variables']
    assert finished['trial']['reward']['kind'] == 'codex' and finished['trial']['reward']['story']
    assert result['accepted_trial']['status'] == 'completed'
    assert claim(payload).json() == result
    assert claim({'request_id': str(uuid4())}).json() == result
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points'):
        assert after[key] == before[key]


def test_early_rest_trial_requires_three_consecutive_distinct_china_days_before_2230(client, auth_headers, letter_clock):
    letter_clock(datetime(2026, 9, 14, 10, tzinfo=timezone.utc))
    original = next(row for row in letters(client, auth_headers)['letters'] if row['senior_key'] == 'qingheng')
    assert original['trial']['key'] == 'early_rest'
    path = f"/api/cave/letters/{original['id']}"
    assert client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200

    def complete(day, hour=13, minute=0):
        letter_clock(datetime(2026, 9, day, hour, minute, tzinfo=timezone.utc))
        started = client.post('/api/cave/sessions', headers=auth_headers, json={'request_id': str(uuid4()), 'target_duration': 1})
        assert started.status_code == 200, started.text
        letter_clock(datetime(2026, 9, day, hour, minute + 1, tzinfo=timezone.utc))
        settled = client.post(f"/api/cave/sessions/{started.json()['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())})
        assert settled.status_code == 200, settled.text

    complete(14)
    complete(14, minute=5)  # Multiple sessions on the same China day count once.
    assert client.get(path, headers=auth_headers).json()['trial']['current'] == 1
    complete(15, hour=14, minute=29)  # Exactly 22:30 is not before 22:30.
    complete(16)
    complete(17)
    assert client.get(path, headers=auth_headers).json()['trial']['current'] == 2
    assert client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    complete(18)
    ready = client.get(path, headers=auth_headers).json()
    assert ready['trial']['current'] == 3 and ready['trial']['status'] == 'ready'
    letter_clock(datetime(2026, 9, 21, 2, tzinfo=timezone.utc))
    claimed = client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())})
    assert claimed.status_code == 200, claimed.text  # Proof stays in its original week even if claimed later.
    finished = next(row for row in claimed.json()['letters'] if row['id'] == original['id'])
    assert finished['trial']['reward']['key'] == 'trial:early_rest'


def test_old_task_trial_requires_own_task_older_than_three_days_completed_after_acceptance(
    client, auth_headers, letter_clock, db_session, user
):
    from app.models.todo import Task

    letter_clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    old = Task(user_id=user.id, title='重新拿起的旧事', created_at=datetime(2026, 9, 9, 2))
    boundary = Task(user_id=user.id, title='刚好三天', created_at=datetime(2026, 9, 11, 2, 1))
    db_session.add_all([old, boundary,
        Task(user_id=user.id, title='先前做完', status='completed', created_at=datetime(2026, 9, 9), completed_at=datetime(2026, 9, 14, 1)),
        Task(user_id=uuid4(), title='别人的旧事', status='completed', created_at=datetime(2026, 9, 9), completed_at=datetime(2026, 9, 14, 2, 1)),
    ])
    db_session.commit()
    original = next(row for row in letters(client, auth_headers)['letters'] if row['senior_key'] == 'lifeng')
    assert original['trial']['key'] == 'old_task'
    path = f"/api/cave/letters/{original['id']}"
    assert client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert client.get(path, headers=auth_headers).json()['trial']['current'] == 0
    letter_clock(datetime(2026, 9, 14, 2, 1, tzinfo=timezone.utc))
    assert client.post(f'/api/todos/tasks/{boundary.id}/complete', headers=auth_headers).status_code == 200
    assert client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    letter_clock(datetime(2026, 9, 14, 2, 2, tzinfo=timezone.utc))
    assert client.post(f'/api/todos/tasks/{old.id}/complete', headers=auth_headers).status_code == 200
    assert client.get(path, headers=auth_headers).json()['trial']['status'] == 'ready'
    response = client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())})
    assert response.status_code == 200, response.text
    finished = next(row for row in response.json()['letters'] if row['id'] == original['id'])
    assert finished['trial']['reward']['key'] == 'trial:old_task'


def test_long_sitting_trial_needs_one_full_ninety_minute_session_after_acceptance(
    client, auth_headers, letter_clock, db_session, user
):
    from app.models.cultivation_retreat import CultivationRetreat

    letter_clock(datetime(2026, 9, 21, 2, tzinfo=timezone.utc))
    db_session.add(CultivationRetreat(user_id=user.id, target_duration=90, actual_duration=90,
        status='completed', started_at=datetime(2026, 9, 20, 16), ended_at=datetime(2026, 9, 20, 17, 30)))
    db_session.commit()
    original = next(row for row in letters(client, auth_headers)['letters'] if row['senior_key'] == 'lifeng')
    assert original['trial']['key'] == 'long_sitting'
    path = f"/api/cave/letters/{original['id']}"
    assert client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    started = client.post('/api/cave/sessions', headers=auth_headers, json={'request_id': str(uuid4()), 'target_duration': 90}).json()
    letter_clock(datetime(2026, 9, 21, 3, 29, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    started = client.post('/api/cave/sessions', headers=auth_headers, json={'request_id': str(uuid4()), 'target_duration': 90}).json()
    letter_clock(datetime(2026, 9, 21, 4, 59, tzinfo=timezone.utc))
    assert client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert client.get(path, headers=auth_headers).json()['trial']['status'] == 'ready'
    result = client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())})
    assert result.status_code == 200, result.text
    finished = next(row for row in result.json()['letters'] if row['id'] == original['id'])
    assert finished['trial']['reward']['key'] == 'trial:long_sitting'


def test_senior_unlocks_trial_stories_and_unread_counts_share_cave_growth_and_codex(
    client, auth_headers, letter_clock, db_session, user
):
    from app.models.todo import Task

    assert client.get('/api/cave/today', headers=auth_headers).json()['unread_letters_count'] == 0
    letter_clock(datetime(2026, 9, 6, 16, tzinfo=timezone.utc))
    today = client.get('/api/cave/today', headers=auth_headers).json()
    assert today['unread_letters_count'] == 1
    seniors = {row['key']: row for row in today['companions']['seniors']}
    assert seniors['qingheng']['unlocked'] is True and seniors['lifeng']['unlocked'] is False
    first_unlock = seniors['qingheng']['first_unlocked_at']
    letter_clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    today = client.get('/api/cave/today', headers=auth_headers).json()
    assert today['unread_letters_count'] == 3
    assert today['companions']['seniors'][0]['first_unlocked_at'] == first_unlock
    assert all(row['unlocked'] for row in today['companions']['seniors'])
    inbox = letters(client, auth_headers)
    brother = next(row for row in inbox['letters'] if row['senior_key'] == 'lifeng')
    path = f"/api/cave/letters/{brother['id']}"
    task = Task(user_id=user.id, title='收好一件旧事', created_at=datetime(2026, 9, 1))
    db_session.add(task)
    db_session.commit()
    assert client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    letter_clock(datetime(2026, 9, 14, 2, 1, tzinfo=timezone.utc))
    assert client.post(f'/api/todos/tasks/{task.id}/complete', headers=auth_headers).status_code == 200
    claimed = client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())})
    assert claimed.status_code == 200, claimed.text
    assert client.get('/api/cave/today', headers=auth_headers).json()['unread_letters_count'] == 2
    codex = client.get('/api/cave/codex', headers=auth_headers).json()
    assert [row['key'] for row in codex['categories']] == ['encounters', 'pets', 'seniors', 'locations', 'techniques']
    senior_category = next(row for row in codex['categories'] if row['key'] == 'seniors')
    entries = {row['key']: row for row in senior_category['entries']}
    assert senior_category['unlocked'] == 3
    assert entries['qingheng']['first_unlocked_at'] == first_unlock
    story = entries['trial:old_task']
    assert story['unlocked'] is True and story['unlock_count'] == 1 and story['story']
    assert story['first_unlocked_at'] is not None
    assert client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert client.get('/api/cave/codex', headers=auth_headers).json() == codex
    growth = client.get('/api/cave/growth', headers=auth_headers).json()
    assert growth['codex_counts'] == [{key: row[key] for key in ('key', 'name', 'unlocked', 'total')} for row in codex['categories']]


def test_letter_actions_progress_and_story_rewards_are_user_isolated_with_owner_404(
    client, auth_headers, letter_clock, db_session, user
):
    from app.models.user import User
    from app.models.todo import Task
    from app.services.auth import create_access_token

    letter_clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused', created_at=datetime(2026, 9, 1))
    db_session.add(other)
    db_session.commit()
    other_headers = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    own = letters(client, auth_headers)
    theirs = letters(client, other_headers)
    foreign = theirs['letters'][0]
    foreign_path = f"/api/cave/letters/{foreign['id']}"
    assert client.get(foreign_path, headers=auth_headers).status_code == 404
    for action in ('read', 'accept', 'decline', 'claim'):
        assert client.post(f'{foreign_path}/{action}', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 404
        assert client.post(f'/api/cave/letters/{uuid4()}/{action}', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 404
    assert letters(client, other_headers) == theirs
    assert letters(client, auth_headers) == own
    selected = next(row for row in own['letters'] if row['senior_key'] == 'lifeng')
    other_selected = next(row for row in theirs['letters'] if row['senior_key'] == 'lifeng')
    same_request = {'request_id': str(uuid4())}
    own_path = f"/api/cave/letters/{selected['id']}"
    other_path = f"/api/cave/letters/{other_selected['id']}"
    assert client.post(f'{own_path}/accept', headers=auth_headers, json=same_request).status_code == 200
    assert client.post(f'{other_path}/accept', headers=other_headers, json=same_request).status_code == 200
    task = Task(user_id=user.id, title='只属于自己的旧事', created_at=datetime(2026, 9, 1))
    db_session.add(task)
    db_session.commit()
    letter_clock(datetime(2026, 9, 14, 2, 1, tzinfo=timezone.utc))
    assert client.post(f'/api/todos/tasks/{task.id}/complete', headers=auth_headers).status_code == 200
    assert client.get(own_path, headers=auth_headers).json()['trial']['status'] == 'ready'
    assert client.get(other_path, headers=other_headers).json()['trial']['current'] == 0
    assert client.post(f'{other_path}/claim', headers=other_headers, json={'request_id': str(uuid4())}).status_code == 409
    assert client.post(f'{own_path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    codex = client.get('/api/cave/codex', headers=other_headers).json()
    stories = next(row for row in codex['categories'] if row['key'] == 'seniors')['entries']
    assert not next(row for row in stories if row['key'] == 'trial:old_task')['unlocked']


def test_concurrent_delivery_acceptance_and_claim_keep_one_weekly_choice_and_one_story(
    client, auth_headers, letter_clock, database, user, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker
    from app.database import get_db
    from app.main import app
    from app.models.user import User
    from app.models.todo import Task
    from app.models.cultivation_retreat import CultivationRetreat

    letter_clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    database.add(User(id=user.id, username='letters-race', email='letters-race@example.com', password_hash='unused',
                      created_at=datetime(2026, 9, 1)))
    database.commit()
    sessions = sessionmaker(bind=database.get_bind())

    def get_file_db():
        with sessions() as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, get_file_db)

    def concurrent(operation, values):
        barrier = Barrier(2)

        def invoke(value):
            barrier.wait(timeout=10)
            return operation(value)

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(invoke, values))

    delivered = concurrent(lambda _: letters(client, auth_headers), [0, 1])
    assert delivered[0] == delivered[1] and len(delivered[0]['letters']) == 2
    ids = [row['id'] for row in delivered[0]['letters']]
    responses = concurrent(lambda id: client.post(f'/api/cave/letters/{id}/accept', headers=auth_headers,
                                                  json={'request_id': str(uuid4())}), ids)
    assert sorted(response.status_code for response in responses) == [200, 409]
    current = letters(client, auth_headers)
    assert sum(row['status'] == 'accepted' for row in current['letters']) == 1
    accepted = current['accepted_trial']['letter_id']
    database.add(Task(user_id=user.id, title='并发试炼旧事', status='completed', created_at=datetime(2026, 9, 1),
                      completed_at=datetime(2026, 9, 14, 3)))
    for day in (14, 15, 16):
        database.add(CultivationRetreat(user_id=user.id, target_duration=25, actual_duration=25, status='completed',
            started_at=datetime(2026, 9, day, 3), ended_at=datetime(2026, 9, day, 3, 25)))
    database.commit()
    letter_clock(datetime(2026, 9, 16, 4, tzinfo=timezone.utc))
    claims = concurrent(lambda _: client.post(f'/api/cave/letters/{accepted}/claim', headers=auth_headers,
                                               json={'request_id': str(uuid4())}), [0, 1])
    assert [response.status_code for response in claims] == [200, 200]
    assert claims[0].json() == claims[1].json()
    codex = client.get('/api/cave/codex', headers=auth_headers).json()
    stories = next(row for row in codex['categories'] if row['key'] == 'seniors')['entries']
    assert sum(row['unlock_count'] for row in stories if row['key'].startswith('trial:')) == 1


def test_trial_proof_cannot_cross_the_exclusive_china_week_end(client, auth_headers, letter_clock):
    letter_clock(datetime(2026, 9, 7, 14, tzinfo=timezone.utc))
    original = letters(client, auth_headers)['letters'][0]
    path = f"/api/cave/letters/{original['id']}"
    assert client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    letter_clock(datetime(2026, 9, 13, 15, 35, tzinfo=timezone.utc))
    started = client.post('/api/cave/sessions', headers=auth_headers, json={'request_id': str(uuid4()), 'target_duration': 25}).json()
    letter_clock(datetime(2026, 9, 13, 16, tzinfo=timezone.utc))  # Exactly Monday 00:00 China.
    assert client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    old = client.get(path, headers=auth_headers).json()
    assert old['trial']['current'] == 0 and old['trial']['can_accept'] is False
    assert client.post(f'{path}/claim', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    assert old['body'] == original['body'] and old['variables'] == original['variables']


def test_failed_claim_commit_rolls_back_the_story_and_remains_retryable(
    client, auth_headers, letter_clock, db_session, user
):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from app.models.todo import Task

    letter_clock(datetime(2026, 9, 14, 2, tzinfo=timezone.utc))
    original = next(row for row in letters(client, auth_headers)['letters'] if row['senior_key'] == 'lifeng')
    path = f"/api/cave/letters/{original['id']}"
    task = Task(user_id=user.id, title='准备收好的旧事', created_at=datetime(2026, 9, 1))
    db_session.add(task)
    db_session.commit()
    assert client.post(f'{path}/accept', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    letter_clock(datetime(2026, 9, 14, 2, 1, tzinfo=timezone.utc))
    assert client.post(f'/api/todos/tasks/{task.id}/complete', headers=auth_headers).status_code == 200
    db_session.execute(text("CREATE TRIGGER fail_story_claim BEFORE INSERT ON cave_requests "
                            "WHEN NEW.operation = 'letter_claim' BEGIN SELECT RAISE(ABORT, 'story write failed'); END"))
    db_session.commit()
    payload = {'request_id': str(uuid4())}
    with pytest.raises(IntegrityError, match='story write failed'):
        client.post(f'{path}/claim', headers=auth_headers, json=payload)
    ready = client.get(path, headers=auth_headers).json()
    assert ready['trial']['status'] == 'ready' and ready['trial']['reward'] is None
    codex = client.get('/api/cave/codex', headers=auth_headers).json()
    entries = next(row for row in codex['categories'] if row['key'] == 'seniors')['entries']
    assert next(row for row in entries if row['key'] == 'trial:old_task')['unlock_count'] == 0
    db_session.execute(text('DROP TRIGGER fail_story_claim'))
    db_session.commit()
    retried = client.post(f'{path}/claim', headers=auth_headers, json=payload)
    assert retried.status_code == 200, retried.text
    assert next(row for row in retried.json()['letters'] if row['id'] == original['id'])['trial']['status'] == 'completed'


def test_first_sister_letter_arrives_on_china_calendar_day_seven(client, auth_headers, letter_clock):
    assert letters(client, auth_headers) == {'letters': [], 'unread_count': 0, 'accepted_trial': None}
    letter_clock(datetime(2026, 9, 6, 16, tzinfo=timezone.utc))
    result = letters(client, auth_headers)
    assert result['unread_count'] == 1
    assert len(result['letters']) == 1
    letter = result['letters'][0]
    assert letter['senior_key'] == 'qingheng' and letter['senior_name'] == '师姐·青蘅'
    assert letter['week_start'] == '2026-09-07'
    assert letter['status'] == 'unread' and letter['read_at'] is None
    assert letter['variables'] == {'completed_tasks': 0, 'best_streak': 0, 'latest_completion_time': None, 'weekly_sessions': 0}
    assert letter['title'] and letter['body'] and letter['trial']['title']
    assert letters(client, auth_headers) == result
