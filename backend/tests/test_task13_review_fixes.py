import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.coin_transaction import CoinTransaction
from app.models.cultivation import CultivationLog, CultivationProfile
from app.models.technique import TechniqueSlot
from app.models.user import User
from app.models.world import Npc, NpcEvent


def test_different_source_keys_in_independent_sessions_accumulate_every_wallet_and_log(
    tmp_path,
):
    from app.services.todo import TodoService

    database_engine = create_engine(
        f"sqlite:///{tmp_path / 'different-source-keys.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    Base.metadata.create_all(bind=database_engine)
    with database_engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL"))
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=database_engine)
    setup = session_factory()
    try:
        user = User(
            username=f"concurrent-{uuid4().hex}",
            email=f"concurrent-{uuid4().hex}@example.com",
            password_hash="hashed",
        )
        setup.add(user)
        setup.commit()
        user_id = user.id
        setup.add(CultivationProfile(user_id=user_id))
        setup.commit()
    finally:
        setup.close()

    barrier = Barrier(2)

    def settle(source_key):
        session = session_factory()
        try:
            stale_user = session.get(User, user_id)
            barrier.wait(timeout=5)
            result = TodoService(session)._update_rewards(
                stale_user,
                20,
                15,
                "task",
                source_key=source_key,
            )
            session.commit()
            return result
        finally:
            session.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(settle, ("todo:task:first", "todo:task:second")))

        verify = session_factory()
        try:
            stored_user = verify.get(User, user_id)
            profile = verify.query(CultivationProfile).filter_by(user_id=user_id).one()
            assert all(result.cultivation == 15 for result in results)
            assert (stored_user.coins, stored_user.total_coins_earned, stored_user.experience) == (
                40,
                40,
                30,
            )
            assert (profile.cultivation, profile.spirit_stones) == (30, 18)
            assert verify.query(CultivationLog).filter_by(user_id=user_id).count() == 2
            assert verify.query(CoinTransaction).filter_by(
                user_id=user_id, source="task"
            ).count() == 2
        finally:
            verify.close()
    finally:
        database_engine.dispose()


def _create_reference_rich_legacy_schema(database_engine):
    Base.metadata.create_all(bind=database_engine)
    with database_engine.begin() as connection:
        for table_name in (
            "techniques",
            "learned_techniques",
            "sects",
            "sect_access_progress",
            "sect_memberships",
        ):
            connection.execute(text(f"DROP TABLE {table_name}"))
        connection.execute(text(
            "CREATE TABLE techniques ("
            "id VARCHAR(36) PRIMARY KEY, technique_key VARCHAR(64) NOT NULL)"
        ))
        connection.execute(text(
            "CREATE TABLE learned_techniques ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "technique_id VARCHAR(36) NOT NULL, learned_at DATETIME NOT NULL, "
            "level INTEGER NOT NULL DEFAULT 1)"
        ))
        connection.execute(text(
            "CREATE TABLE sects ("
            "id VARCHAR(36) PRIMARY KEY, sect_key VARCHAR(64) NOT NULL)"
        ))
        connection.execute(text(
            "CREATE TABLE sect_access_progress ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "sect_id VARCHAR(36) NOT NULL, messenger_contacted BOOLEAN NOT NULL, "
            "trial_confirmed BOOLEAN NOT NULL)"
        ))
        connection.execute(text(
            "CREATE TABLE sect_memberships ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "sect_id VARCHAR(36) NOT NULL, status VARCHAR(20) NOT NULL, "
            "joined_at DATETIME NOT NULL, left_at DATETIME)"
        ))
        connection.execute(text(
            "INSERT INTO techniques (id, technique_key) VALUES "
            "('technique-keeper', 'legacy-technique'), ('technique-old', 'legacy-technique')"
        ))
        connection.execute(text(
            "INSERT INTO learned_techniques "
            "(id, user_id, technique_id, learned_at, level) VALUES "
            "('learned-keeper', 'user-1', 'technique-keeper', '2026-08-16 09:00:00', 1), "
            "('learned-old', 'user-1', 'technique-old', '2026-08-17 09:00:00', 3)"
        ))
        connection.execute(text(
            "INSERT INTO technique_slots (id, user_id, slot_type, slot_index, technique_id) "
            "VALUES ('slot-old', 'user-1', 'combat', 1, 'technique-old')"
        ))
        connection.execute(text(
            "INSERT INTO sects (id, sect_key) VALUES "
            "('sect-keeper', 'legacy-sect'), ('sect-old', 'legacy-sect')"
        ))
        connection.execute(text(
            "INSERT INTO sect_access_progress "
            "(id, user_id, sect_id, messenger_contacted, trial_confirmed) VALUES "
            "('access-keeper', 'user-1', 'sect-keeper', 0, 1), "
            "('access-old', 'user-1', 'sect-old', 1, 0)"
        ))
        connection.execute(text(
            "INSERT INTO sect_memberships "
            "(id, user_id, sect_id, status, joined_at, left_at) VALUES "
            "('membership-keeper', 'user-1', 'sect-keeper', 'left', "
            "'2026-08-17 09:00:00', '2026-08-17 10:00:00'), "
            "('membership-old', 'user-1', 'sect-old', 'active', "
            "'2026-08-16 09:00:00', NULL)"
        ))
        connection.execute(text(
            "INSERT INTO npcs "
            "(id, user_id, sect_id, name, is_core, population_index, is_generated, cultivation, cultivation_locked) "
            "VALUES ('npc-keeper', 'user-1', 'sect-keeper', 'Keeper', 0, 1, 1, 10, 0), "
            "('npc-old', 'user-1', 'sect-old', 'Old', 0, 1, 1, 20, 0)"
        ))
        connection.execute(text(
            "INSERT INTO npc_events "
            "(id, user_id, npc_id, event_key, summary, created_at) VALUES "
            "('event-old', 'user-1', 'npc-old', 'legacy', 'old event', '2026-08-17 12:00:00')"
        ))


def test_legacy_key_migration_merges_all_references_before_unique_constraints(
    tmp_path, monkeypatch
):
    from app import main as main_module

    database_engine = create_engine(f"sqlite:///{tmp_path / 'reference-rich.sqlite'}")
    _create_reference_rich_legacy_schema(database_engine)
    monkeypatch.setattr(main_module, "engine", database_engine)

    main_module._migrate_columns()
    main_module._migrate_columns()

    with database_engine.connect() as connection:
        learned = connection.execute(text(
            "SELECT id, technique_id, level FROM learned_techniques"
        )).fetchall()
        slot = connection.execute(text(
            "SELECT technique_id FROM technique_slots WHERE id = 'slot-old'"
        )).one()
        access = connection.execute(text(
            "SELECT id, sect_id, messenger_contacted, trial_confirmed "
            "FROM sect_access_progress"
        )).fetchall()
        memberships = connection.execute(text(
            "SELECT id, sect_id, status, joined_at, left_at FROM sect_memberships"
        )).fetchall()
        npcs = connection.execute(text(
            "SELECT id, sect_id FROM npcs WHERE user_id = 'user-1'"
        )).fetchall()
        events = connection.execute(text(
            "SELECT npc_id FROM npc_events WHERE id = 'event-old'"
        )).one()

    assert len(learned) == 1
    assert learned[0][1:] == ("technique-keeper", 3)
    assert slot[0] == "technique-keeper"
    assert access == [("access-keeper", "sect-keeper", 1, 1)]
    assert memberships == [
        ("membership-keeper", "sect-keeper", "active", "2026-08-16 09:00:00", None)
    ]
    assert npcs == [("npc-keeper", "sect-keeper")]
    assert events[0] == "npc-keeper"
    database_engine.dispose()


def test_migration_replaces_same_named_sqlite_index_and_keeps_latest_source_settlement(
    tmp_path, monkeypatch
):
    from app import main as main_module

    database_engine = create_engine(f"sqlite:///{tmp_path / 'duplicate-source-logs.sqlite'}")
    Base.metadata.create_all(bind=database_engine)
    with database_engine.begin() as connection:
        connection.execute(text("DROP TABLE cultivation_logs"))
        connection.execute(text(
            "CREATE TABLE cultivation_logs ("
            "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL, "
            "source VARCHAR(64) NOT NULL, source_key VARCHAR(128), "
            "cultivation_delta INTEGER NOT NULL, spirit_stones_delta INTEGER NOT NULL, "
            "merit_delta INTEGER NOT NULL DEFAULT 0, contribution_delta INTEGER NOT NULL DEFAULT 0, "
            "created_at DATETIME NOT NULL)"
        ))
        connection.execute(text(
            "CREATE INDEX uq_cultivation_log_source_key ON cultivation_logs (source_key)"
        ))
        connection.execute(text(
            "INSERT INTO cultivation_logs "
            "(id, user_id, source, source_key, cultivation_delta, spirit_stones_delta, created_at) VALUES "
            "('log-old', 'user-1', 'task', 'todo:task:duplicate', 10, 6, '2026-08-16 09:00:00'), "
            "('log-new', 'user-1', 'task', 'todo:task:duplicate', 15, 9, '2026-08-17 09:00:00')"
        ))
    monkeypatch.setattr(main_module, "engine", database_engine)

    main_module._migrate_columns()
    main_module._migrate_columns()

    indexes = {
        index["name"]: index
        for index in inspect(database_engine).get_indexes("cultivation_logs")
    }
    with database_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, cultivation_delta, spirit_stones_delta "
            "FROM cultivation_logs WHERE source_key = 'todo:task:duplicate'"
        )).fetchall()

    assert bool(indexes["uq_cultivation_log_source_key"]["unique"]) is True
    assert rows == [("log-new", 15, 9)]
    database_engine.dispose()


def test_index_replacement_uses_mysql_and_mssql_drop_syntax():
    from app import main as main_module

    class Dialect:
        def __init__(self, name):
            self.name = name

    class Connection:
        def __init__(self, dialect_name):
            self.dialect = Dialect(dialect_name)
            self.statements = []

        def execute(self, statement):
            self.statements.append(str(statement))

    mysql = Connection("mysql")
    mssql = Connection("mssql")
    main_module._drop_index(mysql, "cultivation_logs", "uq_cultivation_log_source_key")
    main_module._drop_index(mssql, "cultivation_logs", "uq_cultivation_log_source_key")

    assert mysql.statements == [
        "DROP INDEX `uq_cultivation_log_source_key` ON `cultivation_logs`"
    ]
    assert mssql.statements == [
        "DROP INDEX [uq_cultivation_log_source_key] ON [cultivation_logs]"
    ]
