from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.cultivation_retreat import CultivationRetreat


@pytest.fixture
def cave_clock(clock, monkeypatch):
    instant = [datetime(2026, 9, 12, 2, tzinfo=timezone.utc)]

    def set_time(value):
        instant[0] = value
        clock(value)

    monkeypatch.setattr('app.services.cultivation_retreat.utc_now', lambda: instant[0])
    monkeypatch.setattr('app.services.encounter_engine.random.random', lambda: 1.0)
    set_time(instant[0])
    return set_time


def read(client, headers, path):
    response = client.get(f'/api/cave/{path}', headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def historical_sessions(db, user_id, count):
    for index in range(count):
        ended = datetime(2026, 9, 1, 2) + timedelta(days=index)
        db.add(CultivationRetreat(user_id=user_id, target_duration=25, actual_duration=25,
                                 status='completed', started_at=ended - timedelta(minutes=25), ended_at=ended))
    db.commit()


@pytest.mark.parametrize('count,unlocked,familiarity', [(2, [], 2), (3, ['white_deer'], 3),
    (7, ['white_deer', 'spirit_fox'], 5), (14, ['white_deer', 'spirit_fox', 'cloud_crane'], 5)])
def test_pet_milestones_are_durable_and_do_not_automatically_select_a_pet(
    client, auth_headers, db_session, user, cave_clock, count, unlocked, familiarity
):
    historical_sessions(db_session, user.id, count)
    result = read(client, auth_headers, 'companions')
    assert [pet['key'] for pet in result['pets'] if pet['unlocked']] == unlocked
    assert result['dao_child']['familiarity'] == familiarity
    assert result['active_pet_key'] is None
    for pet in result['pets']:
        if pet['unlocked']:
            assert pet['first_unlocked_at'] is not None
            assert pet['unlock_count'] == 1
    cave_clock(datetime(2026, 10, 1, 2, tzinfo=timezone.utc))
    assert read(client, auth_headers, 'companions') == result


def test_unlocked_pets_switch_freely_with_one_active_and_request_replay(
    client, auth_headers, db_session, user, cave_clock
):
    historical_sessions(db_session, user.id, 14)
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    first_payload = {'request_id': str(uuid4())}
    first = client.post('/api/cave/companions/white_deer/activate', headers=auth_headers, json=first_payload)
    assert first.status_code == 200, first.text
    assert first.json()['active_pet_key'] == 'white_deer'
    for key in ('spirit_fox', 'cloud_crane'):
        response = client.post(f'/api/cave/companions/{key}/activate', headers=auth_headers, json={'request_id': str(uuid4())})
        assert response.status_code == 200, response.text
        assert [pet['key'] for pet in response.json()['pets'] if pet['active']] == [key]
    assert read(client, auth_headers, 'companions')['active_pet_key'] == 'cloud_crane'
    assert client.post('/api/cave/companions/white_deer/activate', headers=auth_headers, json=first_payload).json() == first.json()
    assert read(client, auth_headers, 'companions')['active_pet_key'] == 'cloud_crane'
    assert client.post('/api/cave/companions/spirit_fox/activate', headers=auth_headers, json=first_payload).status_code == 409
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points'):
        assert after[key] == before[key]


def test_codex_aggregates_five_categories_from_user_owned_records(
    client, auth_headers, db_session, user, cave_clock
):
    from app.models.cultivation_retreat import EncounterEvent, UserEncounterRecord
    from app.models.technique import Technique, LearnedTechnique
    from app.models.world import WorldNode, WorldNodeProgress

    moment = datetime(2026, 9, 10, 3)
    event = EncounterEvent(id='growth-encounter', title='山泉回响', story_text='泉水记得这段路。',
                           rarity='rare', reward_type='exp', reward_payload={})
    known = WorldNode(node_key='growth-known', name='旧路', description='林间的旧路。', sort_order=100)
    foreign = WorldNode(node_key='growth-foreign', name='远山', description='山在远处。', sort_order=101, completed=True)
    technique = Technique(technique_key='growth-technique', name='息心诀', description='一呼一吸。', technique_type='mind')
    db_session.add_all([event, known, foreign, technique])
    db_session.flush()
    db_session.add_all([
        UserEncounterRecord(user_id=user.id, encounter_id=event.id, first_unlocked_at=moment, unlock_count=2),
        WorldNodeProgress(user_id=user.id, node_id=known.id, completed=True, completed_at=moment),
        WorldNodeProgress(user_id=uuid4(), node_id=foreign.id, completed=True, completed_at=moment),
        LearnedTechnique(user_id=user.id, technique_id=technique.id, learned_at=moment),
    ])
    db_session.commit()
    result = read(client, auth_headers, 'codex')
    categories = {category['key']: category for category in result['categories']}
    assert list(categories) == ['encounters', 'pets', 'seniors', 'locations', 'techniques']
    assert categories['encounters']['unlocked'] == 1
    encounter = next(entry for entry in categories['encounters']['entries'] if entry['key'] == event.id)
    assert (encounter['name'], encounter['rarity'], encounter['story'], encounter['unlock_count']) == ('山泉回响', 'rare', '泉水记得这段路。', 2)
    assert encounter['first_unlocked_at'].startswith('2026-09-10T03:00:00')
    assert categories['pets']['unlocked'] == 1  # Rare encounter unlocks the fox, not the deer.
    locations = {entry['key']: entry for entry in categories['locations']['entries']}
    assert locations['growth-known']['unlocked'] is True
    assert locations['growth-foreign']['unlocked'] is False
    learned = next(entry for entry in categories['techniques']['entries'] if entry['key'] == 'growth-technique')
    assert learned['unlocked'] is True and learned['unlock_count'] == 1
    for category in categories.values():
        assert category['total'] == len(category['entries'])
        for entry in category['entries']:
            assert entry['name'] and entry['story'] and entry['rarity']
            if not entry['unlocked']:
                assert entry['hint'] and entry['first_unlocked_at'] is None and entry['unlock_count'] == 0


def test_growth_and_cave_share_realm_codex_counts_and_the_next_pet_milestone(
    client, auth_headers, db_session, user, cave_clock
):
    historical_sessions(db_session, user.id, 3)
    growth = read(client, auth_headers, 'growth')
    assert growth['realm'] == client.get('/api/cultivation/overview', headers=auth_headers).json()
    assert growth['successful_sessions'] == 3
    assert growth['next_unlock'] == {'key': 'spirit_fox', 'name': '灵狐·照夜', 'current': 3, 'target': 7, 'unlocked': False}
    codex = read(client, auth_headers, 'codex')
    assert growth['codex_counts'] == [{key: category[key] for key in ('key', 'name', 'unlocked', 'total')} for category in codex['categories']]
    today = read(client, auth_headers, 'today')
    assert today['companions'] == growth['companions']
    assert today['next_unlock'] == growth['next_unlock']
    assert today['daily_note'] is None


def test_daily_companion_story_is_one_per_china_day_even_after_switching_pets(
    client, auth_headers, db_session, user, cave_clock
):
    historical_sessions(db_session, user.id, 14)
    cave_clock(datetime(2026, 9, 12, 15, 59, tzinfo=timezone.utc))
    before = client.get('/api/cultivation/overview', headers=auth_headers).json()
    first = client.post('/api/cave/companions/white_deer/activate', headers=auth_headers, json={'request_id': str(uuid4())}).json()
    note = first['daily_note']
    assert note is not None and note['companion_key'] == 'white_deer'
    assert note['date'] == '2026-09-12' and note['story']
    for pet in ('spirit_fox', 'cloud_crane'):
        switched = client.post(f'/api/cave/companions/{pet}/activate', headers=auth_headers, json={'request_id': str(uuid4())}).json()
        assert switched['daily_note'] == note
        assert read(client, auth_headers, 'today')['daily_note'] == note
    cave_clock(datetime(2026, 9, 12, 16, tzinfo=timezone.utc))
    tomorrow = read(client, auth_headers, 'companions')['daily_note']
    assert tomorrow['date'] == '2026-09-13' and tomorrow['key'] != note['key']
    assert tomorrow['companion_key'] == 'cloud_crane'
    assert read(client, auth_headers, 'companions')['daily_note'] == tomorrow
    after = client.get('/api/cultivation/overview', headers=auth_headers).json()
    for key in ('cultivation', 'spirit_stones', 'merit', 'mind_state', 'contribution', 'aptitude_points'):
        assert after[key] == before[key]


def test_daily_note_migration_is_nullable_idempotent_and_preserves_old_signs(
    client, auth_headers, db_session, cave_clock, run_startup_migrations
):
    from sqlalchemy import text

    before = read(client, auth_headers, 'today')
    for column in ('offline_note_key', 'offline_note'):
        db_session.execute(text(f'ALTER TABLE cave_daily_states DROP COLUMN {column}'))
    db_session.commit()
    run_startup_migrations(db_session)
    run_startup_migrations(db_session)
    after = read(client, auth_headers, 'today')
    for key in ('date', 'fortune', 'signs', 'reroll_used'):
        assert after[key] == before[key]
    assert after['daily_note'] is None


def test_session_companion_is_frozen_at_start_and_receipt_survives_later_switches(
    client, auth_headers, db_session, user, cave_clock
):
    historical_sessions(db_session, user.id, 14)
    selected = client.post('/api/cave/companions/spirit_fox/activate', headers=auth_headers, json={'request_id': str(uuid4())})
    assert selected.status_code == 200
    started = client.post('/api/cave/sessions', headers=auth_headers,
                          json={'request_id': str(uuid4()), 'target_duration': 25}).json()
    assert started['companion_snapshot'] == {'key': 'spirit_fox', 'name': '灵狐·照夜'}
    client.post('/api/cave/companions/cloud_crane/activate', headers=auth_headers, json={'request_id': str(uuid4())})
    assert read(client, auth_headers, f"sessions/{started['id']}")['session']['companion_snapshot'] == started['companion_snapshot']
    cave_clock(datetime(2026, 9, 12, 2, 25, tzinfo=timezone.utc))
    response = client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())})
    assert response.status_code == 200, response.text
    settled = response.json()
    assert settled['return_summary']['context']['companion'] == started['companion_snapshot']
    assert '照夜' in settled['return_summary']['narrative']
    companions = read(client, auth_headers, 'companions')
    assert {pet['key']: pet['familiarity'] for pet in companions['pets']} == {'white_deer': 0, 'spirit_fox': 1, 'cloud_crane': 0}
    client.post('/api/cave/companions/white_deer/activate', headers=auth_headers, json={'request_id': str(uuid4())})
    assert read(client, auth_headers, f"sessions/{started['id']}")['session'] == settled
    replay = client.post(f"/api/cave/sessions/{started['id']}/settle", headers=auth_headers, json={'request_id': str(uuid4())})
    assert replay.json() == settled


@pytest.mark.parametrize('source,success,unlocked', [
    ('rare', True, ['spirit_fox']), ('epic', True, ['spirit_fox']), ('legendary', True, ['spirit_fox']),
    ('breakthrough', True, ['cloud_crane']), ('breakthrough', False, []),
])
def test_early_pet_unlock_sources_and_companion_selection_are_user_scoped(
    client, auth_headers, db_session, user, cave_clock, source, success, unlocked
):
    from app.models.cultivation import TribulationAttempt
    from app.models.cultivation_retreat import EncounterEvent, UserEncounterRecord
    from app.models.user import User
    from app.services.auth import create_access_token

    other = User(username=uuid4().hex, email=f'{uuid4().hex}@example.com', password_hash='unused')
    db_session.add(other)
    db_session.flush()
    if source == 'breakthrough':
        db_session.add(TribulationAttempt(user_id=other.id, target_realm='foundation', base_probability=0.8,
            readiness_score=1, final_probability=0.8, roll=0.1, success=success, cultivation_loss=0))
    else:
        event = EncounterEvent(id='early-unlock', title='山间相逢', story_text='一点山中来信。', rarity=source,
                               reward_type='exp', reward_payload={})
        db_session.add(event)
        db_session.add(UserEncounterRecord(user_id=other.id, encounter_id=event.id, unlock_count=1))
    db_session.commit()
    other_auth = {'Authorization': 'Bearer ' + create_access_token({'sub': str(other.id)})}
    own = read(client, auth_headers, 'companions')
    assert not any(pet['unlocked'] for pet in own['pets'])
    theirs = read(client, other_auth, 'companions')
    assert [pet['key'] for pet in theirs['pets'] if pet['unlocked']] == unlocked
    assert client.post('/api/cave/companions/spirit_fox/activate', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 409
    assert client.post('/api/cave/companions/missing/activate', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 404
    if unlocked:
        key = unlocked[0]
        assert client.post(f'/api/cave/companions/{key}/activate', headers=other_auth, json={'request_id': str(uuid4())}).status_code == 200
        assert read(client, auth_headers, 'companions') == own
        assert read(client, other_auth, 'companions')['active_pet_key'] == key


def test_companion_migration_never_backfills_old_active_sessions_or_frozen_receipts(
    client, auth_headers, db_session, user, cave_clock, run_startup_migrations
):
    from sqlalchemy import text

    historical_sessions(db_session, user.id, 3)
    active = CultivationRetreat(user_id=user.id, target_duration=25, status='active', started_at=datetime(2026, 9, 12, 2))
    old = CultivationRetreat(user_id=user.id, target_duration=25, status='completed', started_at=datetime(2026, 9, 10, 2),
        ended_at=datetime(2026, 9, 10, 2, 25), rule_version='b_v1', return_summary={'narrative': '旧时山风。', 'context': {'companion': None}})
    db_session.add_all([active, old])
    db_session.commit()
    active_id, old_id = str(active.id), str(old.id)
    before = read(client, auth_headers, f'sessions/{old_id}')['session']
    db_session.execute(text('ALTER TABLE cultivation_retreats DROP COLUMN companion_snapshot'))
    db_session.commit()
    db_session.expunge_all()
    run_startup_migrations(db_session)
    run_startup_migrations(db_session)
    assert client.post('/api/cave/companions/white_deer/activate', headers=auth_headers, json={'request_id': str(uuid4())}).status_code == 200
    assert read(client, auth_headers, f'sessions/{old_id}')['session'] == before
    assert read(client, auth_headers, f'sessions/{active_id}')['session']['companion_snapshot'] is None


def test_concurrent_pet_switches_share_one_daily_note_and_preserve_one_active_pet(
    client, auth_headers, database, user, cave_clock, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy.orm import sessionmaker
    from app.database import get_db
    from app.main import app
    from app.models.user import User

    database.add(User(id=user.id, username='concurrent-companion', email='companion@example.com', password_hash='unused'))
    database.commit()
    historical_sessions(database, user.id, 14)
    sessions = sessionmaker(bind=database.get_bind())

    def get_file_db():
        with sessions() as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, get_file_db)
    barrier = Barrier(2)

    def activate(key):
        barrier.wait(timeout=10)
        response = client.post(f'/api/cave/companions/{key}/activate', headers=auth_headers, json={'request_id': str(uuid4())})
        assert response.status_code == 200, response.text
        return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(activate, ['white_deer', 'spirit_fox']))
    assert results[0]['daily_note'] == results[1]['daily_note']
    current = read(client, auth_headers, 'companions')
    assert len([pet for pet in current['pets'] if pet['active']]) == 1
    assert current['daily_note'] == results[0]['daily_note']


def test_new_companions_show_locked_pet_hints_and_cosmetic_dao_child(client, auth_headers, cave_clock):
    result = read(client, auth_headers, 'companions')
    assert result['active_pet_key'] is None
    assert result['daily_note'] is None
    assert result['dao_child']['key'] == 'xiaoman'
    assert result['dao_child']['familiarity'] == 0
    assert result['dao_child']['lines']
    assert [(pet['key'], pet['unlocked'], pet['active']) for pet in result['pets']] == [
        ('white_deer', False, False), ('spirit_fox', False, False), ('cloud_crane', False, False),
    ]
    assert all(pet['hint'] and pet['first_unlocked_at'] is None and pet['unlock_count'] == 0 for pet in result['pets'])
    assert [(senior['key'], senior['unlocked']) for senior in result['seniors']] == [('qingheng', False), ('lifeng', False)]
