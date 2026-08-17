import logging
import os
from contextlib import contextmanager

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import CheckConstraint, Column, Integer, MetaData, Table, inspect, select, text
from sqlalchemy.exc import NoSuchTableError, OperationalError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, SessionLocal
from app import models  # noqa: F401  # Register all ORM models before create_all.
from app.services.note import NoteService
from app.api import auth, users, notes, todos, shop, backpack, achievements, checkin, titles, coins, calendar, stats, finance, projects, cultivation

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LifeQuest", version="1.0.0")


logger = logging.getLogger(__name__)

_NOTE_MIGRATION_LOCK_TABLE = "note_migration_lock"


def _generic_note_migration_lock(connection):
    """Create and lock the mutex row using SQLAlchemy's generic SQL constructs."""
    metadata = MetaData()
    lock_table = Table(
        _NOTE_MIGRATION_LOCK_TABLE,
        metadata,
        Column("id", Integer, primary_key=True),
        CheckConstraint("id = 1"),
    )
    lock_table.create(bind=connection, checkfirst=True)

    lock_row = select(lock_table.c.id).where(lock_table.c.id == 1)
    if connection.execute(lock_row).first() is None:
        connection.execute(lock_table.insert().values(id=1))
    connection.execute(lock_row.with_for_update())


def _deduplicate_tribulation_attempts(connection):
    """Keep the latest attempt for each user/day before adding the unique index."""
    rows = connection.execute(text(
        "SELECT id, user_id, attempted_date, attempted_at "
        "FROM tribulation_attempts "
        "WHERE attempted_date IS NOT NULL "
        "ORDER BY user_id, attempted_date, attempted_at DESC, id DESC"
    )).fetchall()
    seen = set()
    for attempt_id, user_id, attempted_date, _attempted_at in rows:
        key = (user_id, attempted_date)
        if key in seen:
            connection.execute(
                text("DELETE FROM tribulation_attempts WHERE id = :id"),
                {"id": attempt_id},
            )
        else:
            seen.add(key)


def _deduplicate_learned_techniques(connection):
    """Keep the latest learned record for each user/technique pair."""
    rows = connection.execute(text(
        "SELECT id, user_id, technique_id, learned_at "
        "FROM learned_techniques "
        "WHERE user_id IS NOT NULL AND technique_id IS NOT NULL "
        "ORDER BY user_id, technique_id, learned_at DESC, id DESC"
    )).fetchall()
    seen = set()
    for learned_id, user_id, technique_id, _learned_at in rows:
        key = (user_id, technique_id)
        if key in seen:
            connection.execute(
                text("DELETE FROM learned_techniques WHERE id = :id"),
                {"id": learned_id},
            )
        else:
            seen.add(key)


def _has_unique_definition(inspector, table_name, column_names):
    column_names = list(column_names)
    try:
        if any(
            constraint.get("column_names") == column_names
            for constraint in inspector.get_unique_constraints(table_name)
        ):
            return True
    except (AttributeError, NotImplementedError, NoSuchTableError):
        pass
    try:
        return any(
            index.get("unique") and index.get("column_names") == column_names
            for index in inspector.get_indexes(table_name)
        )
    except (AttributeError, NotImplementedError, NoSuchTableError):
        return False


def _create_unique_index(connection, table_name, index_name, column_names):
    dialect = getattr(connection, "dialect", None)
    dialect_name = (getattr(dialect, "name", "") or "").lower()
    columns = ", ".join(column_names)
    statement = f"CREATE UNIQUE INDEX {index_name} ON {table_name} ({columns})"
    connection.execute(text(statement))


def _drop_index(connection, table_name, index_name):
    dialect = getattr(connection, "dialect", None)
    dialect_name = (getattr(dialect, "name", "") or "").lower()
    if dialect_name in {"sqlite", "postgresql"}:
        statement = f'DROP INDEX IF EXISTS "{index_name}"'
    elif dialect_name in {"mysql", "mariadb"}:
        statement = f"DROP INDEX `{index_name}` ON `{table_name}`"
    elif dialect_name in {"mssql", "sql server"}:
        statement = f"DROP INDEX [{index_name}] ON [{table_name}]"
    else:
        statement = f"DROP INDEX {index_name}"
    connection.execute(text(statement))


def _ensure_unique_index(connection, table_name, index_name, column_names):
    """Replace a conflicting same-name index, then create the desired guard."""
    inspector = inspect(connection)
    try:
        target = next(
            (index for index in inspector.get_indexes(table_name)
             if index.get("name") == index_name),
            None,
        )
    except (AttributeError, NotImplementedError, NoSuchTableError):
        target = None
    if target and (
        not target.get("unique")
        or target.get("column_names") != list(column_names)
    ):
        _drop_index(connection, table_name, index_name)
        inspector = inspect(connection)

    if _has_unique_definition(inspector, table_name, column_names):
        return
    _create_unique_index(connection, table_name, index_name, column_names)


def _migrate_learned_technique_constraint(inspector, connection):
    """Upgrade legacy learned-technique tables without duplicating fresh DDL."""
    try:
        inspector.get_columns("learned_techniques")
    except (KeyError, NoSuchTableError):
        return

    _deduplicate_learned_techniques(connection)

    _ensure_unique_index(
        connection,
        "learned_techniques",
        "uq_learned_technique_user_technique",
        ["user_id", "technique_id"],
    )


def _deduplicate_npcs(connection):
    """Keep one ordinary disciple and re-parent its events before deleting duplicates."""
    has_events = inspect(connection).has_table("npc_events")
    rows = connection.execute(text(
        "SELECT id, user_id, sect_id, population_index "
        "FROM npcs WHERE population_index IS NOT NULL "
        "ORDER BY user_id, sect_id, population_index, id"
    )).fetchall()
    seen = {}
    for npc_id, user_id, sect_id, population_index in rows:
        key = (user_id, sect_id, population_index)
        if key in seen:
            if has_events:
                connection.execute(
                    text("UPDATE npc_events SET npc_id = :keeper_id WHERE npc_id = :duplicate_id"),
                    {"keeper_id": seen[key], "duplicate_id": npc_id},
                )
            connection.execute(
                text("DELETE FROM npcs WHERE id = :id"),
                {"id": npc_id},
            )
        else:
            seen[key] = npc_id


def _migrate_npc_columns(inspector, connection):
    """Upgrade legacy NPC tables and make ordinary population creation idempotent."""
    try:
        npc_cols = {column["name"] for column in inspector.get_columns("npcs")}
    except (KeyError, NoSuchTableError):
        return

    new_npc_columns = {
        "population_index": "INTEGER",
        "is_generated": "BOOLEAN NOT NULL DEFAULT 0",
        "cultivation": "INTEGER NOT NULL DEFAULT 0",
        "cultivation_updated_on": "DATE",
        "cultivation_locked": "BOOLEAN NOT NULL DEFAULT 0",
    }
    for column_name, column_definition in new_npc_columns.items():
        if column_name in npc_cols:
            continue
        try:
            connection.execute(text(
                f"ALTER TABLE npcs ADD COLUMN {column_name} {column_definition}"
            ))
        except OperationalError as exc:
            error_text = str(getattr(exc, "orig", exc)).lower()
            if "duplicate column" not in error_text or column_name not in error_text:
                raise
        logger.info("Migration: added npcs.%s", column_name)

    _deduplicate_npcs(connection)
    _ensure_unique_index(
        connection,
        "npcs",
        "uq_npc_user_sect_population",
        ["user_id", "sect_id", "population_index"],
    )


def _deduplicate_unique_key_rows(connection, table_name, key_column, references=()):
    rows = connection.execute(text(
        f"SELECT id, {key_column} FROM {table_name} "
        f"WHERE {key_column} IS NOT NULL ORDER BY {key_column}, id"
    )).fetchall()
    seen = {}
    existing_tables = inspect(connection)
    for row_id, key_value in rows:
        keeper_id = seen.get(key_value)
        if keeper_id is None:
            seen[key_value] = row_id
            continue
        if table_name == "techniques":
            _merge_technique_references(connection, row_id, keeper_id)
        elif table_name == "sects":
            _merge_sect_references(connection, row_id, keeper_id)
        for reference_table, reference_column in references:
            if existing_tables.has_table(reference_table):
                connection.execute(text(
                    f"UPDATE {reference_table} SET {reference_column} = :keeper_id "
                    f"WHERE {reference_column} = :duplicate_id"
                ), {"keeper_id": keeper_id, "duplicate_id": row_id})
        connection.execute(
            text(f"DELETE FROM {table_name} WHERE id = :id"),
            {"id": row_id},
        )


def _merge_technique_references(connection, duplicate_id, keeper_id):
    """Move technique references without violating learned-technique uniqueness."""
    if inspect(connection).has_table("learned_techniques"):
        rows = connection.execute(text(
            "SELECT id, user_id, learned_at, level FROM learned_techniques "
            "WHERE technique_id = :duplicate_id ORDER BY id"
        ), {"duplicate_id": duplicate_id}).fetchall()
        for learned_id, user_id, learned_at, level in rows:
            keeper = connection.execute(text(
                "SELECT id, learned_at, level FROM learned_techniques "
                "WHERE user_id = :user_id AND technique_id = :keeper_id"
            ), {"user_id": user_id, "keeper_id": keeper_id}).first()
            if keeper is None:
                connection.execute(text(
                    "UPDATE learned_techniques SET technique_id = :keeper_id "
                    "WHERE id = :learned_id"
                ), {"keeper_id": keeper_id, "learned_id": learned_id})
                continue
            keeper_learned_id, keeper_learned_at, keeper_level = keeper
            connection.execute(text(
                "UPDATE learned_techniques SET learned_at = :learned_at, level = :level "
                "WHERE id = :keeper_id"
            ), {
                "learned_at": max(keeper_learned_at, learned_at),
                "level": max(keeper_level, level),
                "keeper_id": keeper_learned_id,
            })
            connection.execute(text(
                "DELETE FROM learned_techniques WHERE id = :learned_id"
            ), {"learned_id": learned_id})
    if inspect(connection).has_table("technique_slots"):
        connection.execute(text(
            "UPDATE technique_slots SET technique_id = :keeper_id "
            "WHERE technique_id = :duplicate_id"
        ), {"keeper_id": keeper_id, "duplicate_id": duplicate_id})


def _merge_sect_access_reference(connection, duplicate_id, keeper_id):
    if not inspect(connection).has_table("sect_access_progress"):
        return
    rows = connection.execute(text(
        "SELECT id, user_id, messenger_contacted, trial_confirmed "
        "FROM sect_access_progress WHERE sect_id = :duplicate_id ORDER BY id"
    ), {"duplicate_id": duplicate_id}).fetchall()
    for row_id, user_id, contacted, confirmed in rows:
        keeper = connection.execute(text(
            "SELECT id, messenger_contacted, trial_confirmed FROM sect_access_progress "
            "WHERE user_id = :user_id AND sect_id = :keeper_id"
        ), {"user_id": user_id, "keeper_id": keeper_id}).first()
        if keeper is None:
            connection.execute(text(
                "UPDATE sect_access_progress SET sect_id = :keeper_id WHERE id = :row_id"
            ), {"keeper_id": keeper_id, "row_id": row_id})
            continue
        keeper_row_id, keeper_contacted, keeper_confirmed = keeper
        connection.execute(text(
            "UPDATE sect_access_progress SET messenger_contacted = :contacted, "
            "trial_confirmed = :confirmed WHERE id = :row_id"
        ), {
            "contacted": bool(keeper_contacted or contacted),
            "confirmed": bool(keeper_confirmed or confirmed),
            "row_id": keeper_row_id,
        })
        connection.execute(text(
            "DELETE FROM sect_access_progress WHERE id = :row_id"
        ), {"row_id": row_id})


def _merge_sect_membership_reference(connection, duplicate_id, keeper_id):
    if not inspect(connection).has_table("sect_memberships"):
        return
    rows = connection.execute(text(
        "SELECT id, user_id, status, joined_at, left_at FROM sect_memberships "
        "WHERE sect_id = :duplicate_id ORDER BY id"
    ), {"duplicate_id": duplicate_id}).fetchall()
    for row_id, user_id, status, joined_at, left_at in rows:
        keeper = connection.execute(text(
            "SELECT id, status, joined_at, left_at FROM sect_memberships "
            "WHERE user_id = :user_id AND sect_id = :keeper_id"
        ), {"user_id": user_id, "keeper_id": keeper_id}).first()
        if keeper is None:
            connection.execute(text(
                "UPDATE sect_memberships SET sect_id = :keeper_id WHERE id = :row_id"
            ), {"keeper_id": keeper_id, "row_id": row_id})
            continue
        keeper_row_id, keeper_status, keeper_joined_at, keeper_left_at = keeper
        merged_status = "active" if "active" in {status, keeper_status} else keeper_status
        merged_joined_at = min(keeper_joined_at, joined_at)
        left_dates = [value for value in (keeper_left_at, left_at) if value is not None]
        merged_left_at = None if merged_status == "active" or not left_dates else max(left_dates)
        connection.execute(text(
            "UPDATE sect_memberships SET status = :status, joined_at = :joined_at, "
            "left_at = :left_at WHERE id = :row_id"
        ), {
            "status": merged_status,
            "joined_at": merged_joined_at,
            "left_at": merged_left_at,
            "row_id": keeper_row_id,
        })
        connection.execute(text(
            "DELETE FROM sect_memberships WHERE id = :row_id"
        ), {"row_id": row_id})


def _merge_sect_npc_references(connection, duplicate_id, keeper_id):
    if not inspect(connection).has_table("npcs"):
        return
    has_events = inspect(connection).has_table("npc_events")
    rows = connection.execute(text(
        "SELECT id, user_id, population_index FROM npcs "
        "WHERE sect_id = :duplicate_id ORDER BY id"
    ), {"duplicate_id": duplicate_id}).fetchall()
    for npc_id, user_id, population_index in rows:
        keeper_npc = None
        if population_index is not None:
            keeper_npc = connection.execute(text(
                "SELECT id FROM npcs WHERE user_id = :user_id AND sect_id = :keeper_id "
                "AND population_index = :population_index"
            ), {
                "user_id": user_id,
                "keeper_id": keeper_id,
                "population_index": population_index,
            }).scalar()
        if keeper_npc is None:
            connection.execute(text(
                "UPDATE npcs SET sect_id = :keeper_id WHERE id = :npc_id"
            ), {"keeper_id": keeper_id, "npc_id": npc_id})
            continue
        if has_events:
            connection.execute(text(
                "UPDATE npc_events SET npc_id = :keeper_npc WHERE npc_id = :npc_id"
            ), {"keeper_npc": keeper_npc, "npc_id": npc_id})
        connection.execute(text("DELETE FROM npcs WHERE id = :npc_id"), {"npc_id": npc_id})


def _merge_sect_references(connection, duplicate_id, keeper_id):
    _merge_sect_access_reference(connection, duplicate_id, keeper_id)
    _merge_sect_membership_reference(connection, duplicate_id, keeper_id)
    _merge_sect_npc_references(connection, duplicate_id, keeper_id)


def _migrate_unique_key_table(inspector, connection, table_name, key_column, index_name, references=()):
    try:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
    except (KeyError, NoSuchTableError):
        return
    if key_column not in columns:
        return
    live_inspector = inspect(connection)
    if not _has_unique_definition(live_inspector, table_name, [key_column]):
        _deduplicate_unique_key_rows(connection, table_name, key_column, references)
    _ensure_unique_index(connection, table_name, index_name, [key_column])


def _deduplicate_sect_access_rows(connection):
    if not inspect(connection).has_table("sect_access_progress"):
        return
    rows = connection.execute(text(
        "SELECT id, user_id, sect_id, messenger_contacted, trial_confirmed "
        "FROM sect_access_progress ORDER BY user_id, sect_id, id"
    )).fetchall()
    seen = {}
    for row_id, user_id, sect_id, contacted, confirmed in rows:
        key = (user_id, sect_id)
        keeper_id = seen.get(key)
        if keeper_id is None:
            seen[key] = row_id
            continue
        keeper = connection.execute(text(
            "SELECT messenger_contacted, trial_confirmed FROM sect_access_progress "
            "WHERE id = :id"
        ), {"id": keeper_id}).one()
        connection.execute(text(
            "UPDATE sect_access_progress SET messenger_contacted = :contacted, "
            "trial_confirmed = :confirmed WHERE id = :id"
        ), {
            "contacted": bool(keeper[0] or contacted),
            "confirmed": bool(keeper[1] or confirmed),
            "id": keeper_id,
        })
        connection.execute(text(
            "DELETE FROM sect_access_progress WHERE id = :id"
        ), {"id": row_id})


def _migrate_sect_access_constraint(connection):
    if not inspect(connection).has_table("sect_access_progress"):
        return
    _deduplicate_sect_access_rows(connection)
    _ensure_unique_index(
        connection,
        "sect_access_progress",
        "uq_sect_access_user_sect",
        ["user_id", "sect_id"],
    )


def _deduplicate_cultivation_logs(connection):
    """Keep the newest settlement for each legacy non-null source key."""
    rows = connection.execute(text(
        "SELECT id, source_key, created_at FROM cultivation_logs "
        "WHERE source_key IS NOT NULL "
        "ORDER BY source_key, created_at DESC, id DESC"
    )).fetchall()
    seen = set()
    for log_id, source_key, _created_at in rows:
        if source_key in seen:
            connection.execute(text(
                "DELETE FROM cultivation_logs WHERE id = :id"
            ), {"id": log_id})
        else:
            seen.add(source_key)


def _attempted_date_expression(connection):
    dialect = getattr(connection, "dialect", None)
    dialect_name = (getattr(dialect, "name", "") or "").lower()
    if dialect_name in {"sqlite", "mysql", "mariadb"}:
        return "DATE(attempted_at)"
    return "CAST(attempted_at AS DATE)"


@contextmanager
def _note_migration_lock(db_engine):
    """Hold a database-backed mutex across the complete note migration."""
    connection = db_engine.connect()
    transaction = None
    try:
        dialect_name = (getattr(db_engine.dialect, "name", "") or "").lower()
        if dialect_name == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            connection.execute(text(
                f"CREATE TABLE IF NOT EXISTS {_NOTE_MIGRATION_LOCK_TABLE} "
                "(id INTEGER PRIMARY KEY CHECK (id = 1))"
            ))
            connection.execute(text(
                f"INSERT OR IGNORE INTO {_NOTE_MIGRATION_LOCK_TABLE} (id) VALUES (1)"
            ))
        else:
            transaction = connection.begin()
            if dialect_name == "postgresql":
                connection.execute(text(
                    f"CREATE TABLE IF NOT EXISTS {_NOTE_MIGRATION_LOCK_TABLE} "
                    "(id INTEGER PRIMARY KEY CHECK (id = 1))"
                ))
                connection.execute(text(
                    f"INSERT INTO {_NOTE_MIGRATION_LOCK_TABLE} (id) VALUES (1) "
                    "ON CONFLICT (id) DO NOTHING"
                ))
                connection.execute(text(
                    f"SELECT id FROM {_NOTE_MIGRATION_LOCK_TABLE} WHERE id = 1 FOR UPDATE"
                ))
            elif dialect_name in {"mysql", "mariadb"}:
                connection.execute(text(
                    f"CREATE TABLE IF NOT EXISTS {_NOTE_MIGRATION_LOCK_TABLE} "
                    "(id INTEGER PRIMARY KEY CHECK (id = 1))"
                ))
                connection.execute(text(
                    f"INSERT IGNORE INTO {_NOTE_MIGRATION_LOCK_TABLE} (id) VALUES (1)"
                ))
                connection.execute(text(
                    f"SELECT id FROM {_NOTE_MIGRATION_LOCK_TABLE} WHERE id = 1 FOR UPDATE"
                ))
            elif dialect_name in {"mssql", "sql server"}:
                connection.execute(text(
                    f"IF OBJECT_ID(N'{_NOTE_MIGRATION_LOCK_TABLE}', N'U') IS NULL "
                    "BEGIN "
                    f"CREATE TABLE {_NOTE_MIGRATION_LOCK_TABLE} "
                    "(id INT NOT NULL PRIMARY KEY CHECK (id = 1)) "
                    "END"
                ))
                connection.execute(text(
                    f"MERGE {_NOTE_MIGRATION_LOCK_TABLE} WITH (HOLDLOCK) AS target "
                    "USING (VALUES (1)) AS source (id) "
                    "ON target.id = source.id "
                    "WHEN NOT MATCHED THEN INSERT (id) VALUES (source.id);"
                ))
                connection.execute(text(
                    f"SELECT id FROM {_NOTE_MIGRATION_LOCK_TABLE} "
                    "WITH (UPDLOCK, HOLDLOCK) WHERE id = 1"
                ))
            else:
                _generic_note_migration_lock(connection)
        yield connection
    except Exception:
        if transaction is not None:
            transaction.rollback()
        else:
            connection.rollback()
        raise
    else:
        if transaction is not None:
            transaction.commit()
        else:
            connection.commit()
    finally:
        connection.close()


def _migrate_note_data():
    """Run note migration and canonicalization under one database mutex."""
    moved_files = []
    with _note_migration_lock(engine) as lock_connection:
        migrate_db = Session(bind=lock_connection)
        try:
            moved_files = NoteService.migrate_old_data(migrate_db)
            NoteService.canonicalize_existing_tags(migrate_db.connection())
            migrate_db.commit()
        except Exception:
            migrate_db.rollback()
            try:
                NoteService.restore_moved_files(moved_files)
            except Exception:
                logger.exception("Failed to restore files after note migration rollback")
            raise
        finally:
            migrate_db.close()


@app.get("/api/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("Health check database probe failed")
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


def _migrate_columns():
    """Add missing columns to existing tables without a full migration tool."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        # habits.last_completed_at
        habit_cols = {c["name"] for c in inspector.get_columns("habits")}
        if "last_completed_at" not in habit_cols:
            conn.execute(text("ALTER TABLE habits ADD COLUMN last_completed_at DATETIME"))
            logger.info("Migration: added habits.last_completed_at")

        # users.total_coins_earned
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "total_coins_earned" not in user_cols:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN total_coins_earned INTEGER NOT NULL DEFAULT 0"
            ))
            # Backfill from current coins balance for existing users
            conn.execute(text(
                "UPDATE users SET total_coins_earned = coins WHERE total_coins_earned = 0"
            ))
            logger.info("Migration: added users.total_coins_earned")

        # project management columns on tasks table
        task_cols = {c["name"] for c in inspector.get_columns("tasks")}
        new_task_cols = {
            "project_id": "VARCHAR(36)",
            "phase_id": "VARCHAR(36)",
            "milestone_id": "VARCHAR(36)",
            "start_date": "DATETIME",
            "priority": "VARCHAR(10) NOT NULL DEFAULT 'medium'",
            "sort_order": "INTEGER NOT NULL DEFAULT 0",
        }
        for col_name, col_def in new_task_cols.items():
            if col_name not in task_cols:
                conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_def}"))
                logger.info("Migration: added tasks.%s", col_name)

        # finance_transactions.recurring_id
        txn_cols = {c["name"] for c in inspector.get_columns("finance_transactions")}
        if "recurring_id" not in txn_cols:
            conn.execute(text(
                "ALTER TABLE finance_transactions ADD COLUMN recurring_id VARCHAR(36)"
            ))
            logger.info("Migration: added finance_transactions.recurring_id")

        # tribulation_attempts.attempted_date and its database-level daily guard.
        # Older databases (and migration-only test doubles) may predate this table.
        try:
            tribulation_cols = {c["name"] for c in inspector.get_columns("tribulation_attempts")}
        except (KeyError, NoSuchTableError):
            tribulation_cols = None
        if tribulation_cols is not None:
            if "attempted_date" not in tribulation_cols:
                conn.execute(text("ALTER TABLE tribulation_attempts ADD COLUMN attempted_date DATE"))
                conn.execute(text(
                    "UPDATE tribulation_attempts SET attempted_date = "
                    f"{_attempted_date_expression(conn)} WHERE attempted_date IS NULL"
                ))
                logger.info("Migration: added tribulation_attempts.attempted_date")
            _deduplicate_tribulation_attempts(conn)
            _ensure_unique_index(
                conn,
                "tribulation_attempts",
                "uq_tribulation_attempt_user_day",
                ["user_id", "attempted_date"],
            )

        # Task 12 reward event identity. Nullable keys preserve legacy logs;
        # todo completions use a stable non-null key going forward.
        try:
            cultivation_log_cols = {c["name"] for c in inspector.get_columns("cultivation_logs")}
        except (KeyError, NoSuchTableError):
            cultivation_log_cols = None
        if cultivation_log_cols is not None:
            if "source_key" not in cultivation_log_cols:
                conn.execute(text("ALTER TABLE cultivation_logs ADD COLUMN source_key VARCHAR(128)"))
                logger.info("Migration: added cultivation_logs.source_key")
            _deduplicate_cultivation_logs(conn)
            _ensure_unique_index(
                conn,
                "cultivation_logs",
                "uq_cultivation_log_source_key",
                ["source_key"],
            )

        _migrate_npc_columns(inspector, conn)
        _migrate_unique_key_table(
            inspector,
            conn,
            "techniques",
            "technique_key",
            "uq_techniques_technique_key",
            (("learned_techniques", "technique_id"), ("technique_slots", "technique_id")),
        )
        _migrate_learned_technique_constraint(inspector, conn)
        _migrate_unique_key_table(
            inspector,
            conn,
            "sects",
            "sect_key",
            "uq_sects_sect_key",
            (("sect_access_progress", "sect_id"), ("sect_memberships", "sect_id"), ("npcs", "sect_id")),
        )
        _migrate_sect_access_constraint(conn)

        # note_nodes.last_opened_at
        note_node_cols = {c["name"] for c in inspector.get_columns("note_nodes")}
        if "last_opened_at" not in note_node_cols:
            try:
                conn.execute(text(
                    "ALTER TABLE note_nodes ADD COLUMN last_opened_at DATETIME"
                ))
            except OperationalError as exc:
                error_text = str(getattr(exc, "orig", exc)).lower()
                if "duplicate column" not in error_text or "last_opened_at" not in error_text:
                    raise
                logger.info("Migration: note_nodes.last_opened_at already exists")
            else:
                logger.info("Migration: added note_nodes.last_opened_at")

        if "tags_normalized" not in note_node_cols:
            try:
                conn.execute(text(
                    "ALTER TABLE note_nodes ADD COLUMN tags_normalized BOOLEAN"
                ))
            except OperationalError as exc:
                error_text = str(getattr(exc, "orig", exc)).lower()
                if "duplicate column" not in error_text or "tags_normalized" not in error_text:
                    raise
                logger.info("Migration: note_nodes.tags_normalized already exists")
            else:
                logger.info("Migration: added note_nodes.tags_normalized")


@app.on_event("startup")
def startup_event():
    """Seed default achievements on application startup."""
    try:
        _migrate_columns()
    except Exception:
        logger.exception("Column migration failed")
        raise
    try:
        _migrate_note_data()
    except Exception:
        logger.exception("Note data migration failed")
        raise
    db = SessionLocal()
    try:
        from app.services.achievement import AchievementService

        service = AchievementService(db)
        service.seed_achievements()
        # Seed default titles
        from app.services.title import TitleService
        title_service = TitleService(db)
        title_service.seed_titles()
        # Seed default finance categories
        from app.services.finance import FinanceService
        FinanceService.seed_categories(db)
        from app.services.cultivation import CultivationService
        CultivationService.seed_world(db)
    except Exception:
        logger.exception("Seed data failed")
        raise
    finally:
        db.close()


# Mount static files directory for uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# CORS middleware
_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(notes.router)
app.include_router(todos.router)
app.include_router(shop.router)
app.include_router(backpack.router)
app.include_router(achievements.router)
app.include_router(checkin.router)
app.include_router(titles.router)
app.include_router(coins.router)
app.include_router(calendar.router)
app.include_router(stats.router)
app.include_router(finance.router)
app.include_router(projects.router)
app.include_router(cultivation.router)

# MCP SSE server — subprocess on internal port, proxied through explicit routes.
_mcp_process = None

@app.on_event("startup")
def start_mcp_server():
    """Start the MCP SSE server as a subprocess on an internal port."""
    global _mcp_process
    if os.environ.get("MCP_AUTOSTART", "false").lower() != "true":
        logger.info("MCP autostart disabled; use supervisor to run the MCP service")
        return
    import subprocess, sys
    mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "..", "mcp_server.py"),
           "--transport", "sse", "--host", "127.0.0.1", "--port", str(mcp_port)]
    try:
        _mcp_process = subprocess.Popen(cmd)
        logger.info("MCP server started on port %d (pid=%d)", mcp_port, _mcp_process.pid)
    except Exception:
        logger.exception("Failed to start MCP server")

@app.on_event("shutdown")
def stop_mcp_server():
    if _mcp_process and _mcp_process.poll() is None:
        _mcp_process.terminate()
        logger.info("MCP server stopped")


# MCP proxy routes — explicit paths that match before SPA catch-all
import httpx

@app.api_route("/mcp/sse", methods=["GET"])
async def mcp_sse_proxy(request: Request):
    """Proxy SSE stream to MCP subprocess."""
    mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    url = f"http://127.0.0.1:{mcp_port}/sse"
    client = httpx.AsyncClient()
    try:
        req = client.build_request("GET", url, headers=dict(request.headers))
        response = await client.send(req, stream=True)
    except httpx.HTTPError:
        await client.aclose()
        return Response(content='{"detail":"MCP service unavailable"}', status_code=503, media_type="application/json")

    async def stream():
        async for chunk in response.aiter_bytes():
            yield chunk
        await response.aclose()
        await client.aclose()

    return StreamingResponse(
        stream(),
        status_code=response.status_code,
        media_type="text/event-stream",
        headers=dict(response.headers),
    )

@app.api_route("/mcp/messages", methods=["POST"])
@app.api_route("/mcp/messages/", methods=["POST"])
async def mcp_messages_proxy(request: Request):
    """Proxy JSON-RPC messages to MCP subprocess."""
    mcp_port = int(os.environ.get("MCP_PORT", "3001"))
    path = "/messages/" if request.url.path.endswith("/") else "/messages"
    qs = f"?{request.url.query}" if request.url.query else ""
    url = f"http://127.0.0.1:{mcp_port}{path}{qs}"
    body = await request.body()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, content=body, headers=dict(request.headers))
    except httpx.HTTPError:
        return Response(content='{"detail":"MCP service unavailable"}', status_code=503, media_type="application/json")
    return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

logger.info("MCP proxy registered at /mcp/sse and /mcp/messages")


# Serve frontend static files (production mode)
_frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend", "dist")
_frontend_dist = os.path.abspath(_frontend_dist)
if os.path.isdir(_frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(_frontend_dist, "assets")), name="frontend-assets")

    from fastapi.responses import FileResponse, JSONResponse

    @app.exception_handler(404)
    async def spa_fallback(request: Request, exc):
        """Serve index.html for unmatched GET requests (SPA client-side routing)."""
        path = request.url.path
        if request.method == "GET" and not path.startswith(("/api/", "/mcp/", "/uploads/")):
            return FileResponse(os.path.join(_frontend_dist, "index.html"))
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
