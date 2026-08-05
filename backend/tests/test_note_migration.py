from datetime import datetime
import threading
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text

from app.models.note import Notebook
from app.models.note_node import NoteNode
from app.models.user import User
from app.database import Base
from app.services.note import NoteService


def test_note_migration_lock_serializes_sqlite_workers(tmp_path):
    from app.main import _note_migration_lock

    lock_engine = create_engine(
        f"sqlite:///{tmp_path / 'migration-lock.sqlite'}",
        connect_args={"check_same_thread": False, "timeout": 5},
    )
    worker_acquired = threading.Event()
    worker_finished = threading.Event()

    def acquire_in_worker():
        with _note_migration_lock(lock_engine):
            worker_acquired.set()
        worker_finished.set()

    with _note_migration_lock(lock_engine):
        worker = threading.Thread(target=acquire_in_worker)
        worker.start()
        assert not worker_acquired.wait(0.2)

    assert worker_acquired.wait(2)
    assert worker_finished.wait(2)
    worker.join(timeout=2)
    assert not worker.is_alive()


def test_note_migration_lock_uses_mysql_insert_ignore(monkeypatch):
    from app.main import _note_migration_lock

    class _Transaction:
        def __init__(self):
            self.committed = False

        def commit(self):
            self.committed = True

        def rollback(self):
            pass

    class _Connection:
        def __init__(self):
            self.statements = []
            self.transaction = _Transaction()

        def begin(self):
            return self.transaction

        def execute(self, statement):
            self.statements.append(str(statement))

        def rollback(self):
            raise AssertionError("lock transaction should use its transaction object")

        def close(self):
            pass

    class _Engine:
        class dialect:
            name = "mysql"

        def __init__(self):
            self.connection = _Connection()

        def connect(self):
            return self.connection

    lock_engine = _Engine()

    with _note_migration_lock(lock_engine):
        pass

    statements = lock_engine.connection.statements
    assert any("INSERT IGNORE" in statement for statement in statements)
    assert any("FOR UPDATE" in statement for statement in statements)
    assert not any("ON CONFLICT" in statement for statement in statements)
    assert lock_engine.connection.transaction.committed is True


def test_note_migration_lock_uses_sql_server_specific_syntax():
    from app.main import _note_migration_lock

    class _Transaction:
        def __init__(self):
            self.committed = False

        def commit(self):
            self.committed = True

        def rollback(self):
            pass

    class _Connection:
        def __init__(self):
            self.statements = []
            self.transaction = _Transaction()

        def begin(self):
            return self.transaction

        def execute(self, statement):
            self.statements.append(str(statement))

        def rollback(self):
            raise AssertionError("lock transaction should use its transaction object")

        def close(self):
            pass

    class _Engine:
        class dialect:
            name = "mssql"

        def __init__(self):
            self.connection = _Connection()

        def connect(self):
            return self.connection

    lock_engine = _Engine()

    with _note_migration_lock(lock_engine):
        pass

    statements = lock_engine.connection.statements
    assert any("IF OBJECT_ID" in statement for statement in statements)
    assert any("MERGE" in statement for statement in statements)
    assert any("UPDLOCK" in statement and "HOLDLOCK" in statement for statement in statements)
    assert not any("CREATE TABLE IF NOT EXISTS" in statement for statement in statements)
    assert not any("ON CONFLICT" in statement for statement in statements)


def test_note_migration_lock_unknown_dialect_uses_generic_strategy(tmp_path):
    from app.main import _note_migration_lock

    lock_engine = create_engine(f"sqlite:///{tmp_path / 'unknown-dialect-lock.sqlite'}")
    lock_engine.dialect.name = "unknown"

    with _note_migration_lock(lock_engine):
        pass

    with lock_engine.connect() as connection:
        assert connection.execute(
            text(f"SELECT COUNT(*) FROM note_migration_lock")
        ).scalar_one() == 1


@pytest.fixture(autouse=True)
def clean_legacy_tables(db_session):
    db_session.execute(text("DROP TABLE IF EXISTS notes"))
    db_session.execute(text("DROP TABLE IF EXISTS folders"))
    db_session.commit()
    yield
    db_session.rollback()
    db_session.execute(text("DROP TABLE IF EXISTS notes"))
    db_session.execute(text("DROP TABLE IF EXISTS folders"))
    db_session.commit()


def _create_legacy_tables(db_session):
    db_session.execute(
        text(
            "CREATE TABLE folders ("
            "id VARCHAR(36) PRIMARY KEY, notebook_id VARCHAR(36), parent_id VARCHAR(36), "
            "name VARCHAR(200), path VARCHAR(1000))"
        )
    )
    db_session.execute(
        text(
            "CREATE TABLE notes ("
            "id VARCHAR(36) PRIMARY KEY, folder_id VARCHAR(36), title VARCHAR(200), "
            "file_path VARCHAR(1000), summary TEXT, tags VARCHAR(500), is_pinned BOOLEAN, "
            "word_count INTEGER, created_at VARCHAR(50), updated_at VARCHAR(50))"
        )
    )


def test_migrate_old_note_timestamps_to_datetime(db_session):
    Base.metadata.create_all(bind=db_session.bind)
    user = User(
        username="migration-user",
        email="migration@example.com",
        password_hash="hashed-password",
    )
    db_session.add(user)
    db_session.flush()
    notebook = Notebook(user_id=user.id, name="Legacy notebook")
    db_session.add(notebook)
    db_session.commit()

    folder_id = uuid4()
    note_id = uuid4()
    _create_legacy_tables(db_session)
    db_session.execute(
        text(
            "INSERT INTO folders (id, notebook_id, parent_id, name, path) "
            "VALUES (:id, :notebook_id, NULL, :name, :path)"
        ),
        {
            "id": str(folder_id),
            "notebook_id": str(notebook.id),
            "name": "Legacy",
            "path": "/Legacy",
        },
    )
    db_session.execute(
        text(
            "INSERT INTO notes (id, folder_id, title, file_path, summary, tags, is_pinned, "
            "word_count, created_at, updated_at) VALUES (:id, :folder_id, :title, NULL, "
            "NULL, NULL, 0, 3, :created_at, :updated_at)"
        ),
        {
            "id": str(note_id),
            "folder_id": str(folder_id),
            "title": "Legacy note",
            "created_at": "2026-01-02T03:04:05+00:00",
            "updated_at": "2026-01-03 04:05:06",
        },
    )
    db_session.commit()

    NoteService.migrate_old_data(db_session)
    db_session.commit()

    migrated = db_session.query(NoteNode).filter(NoteNode.id == note_id).one()
    assert migrated.created_at == datetime(2026, 1, 2, 3, 4, 5)
    assert migrated.updated_at == datetime(2026, 1, 3, 4, 5, 6)
    assert not inspect(db_session.bind).has_table("folders")
    assert not inspect(db_session.bind).has_table("notes")


def test_migrate_old_data_rolls_back_database_and_files_on_move_failure(db_session, monkeypatch, tmp_path):
    Base.metadata.create_all(bind=db_session.bind)
    db_session.query(NoteNode).delete()
    db_session.commit()
    user = User(username="rollback-user", email="rollback@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.flush()
    notebook = Notebook(user_id=user.id, name="Rollback notebook")
    db_session.add(notebook)
    db_session.commit()

    folder_id = uuid4()
    note_id = uuid4()
    old_file = tmp_path / "notes_data" / str(user.id) / "legacy" / "legacy.md"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("legacy content", encoding="utf-8")
    monkeypatch.setattr("app.services.note.NOTES_DIR", tmp_path / "notes_data")
    _create_legacy_tables(db_session)
    db_session.execute(
        text("INSERT INTO folders (id, notebook_id, parent_id, name, path) VALUES (:id, :notebook_id, NULL, :name, :path)"),
        {"id": str(folder_id), "notebook_id": str(notebook.id), "name": "Legacy", "path": "/Legacy"},
    )
    db_session.execute(
        text(
            "INSERT INTO notes (id, folder_id, title, file_path, summary, tags, is_pinned, word_count, created_at, updated_at) "
            "VALUES (:id, :folder_id, :title, :file_path, NULL, NULL, 0, 1, :created_at, :updated_at)"
        ),
        {
            "id": str(note_id),
            "folder_id": str(folder_id),
            "title": "Legacy note",
            "file_path": str(old_file),
            "created_at": "2026-01-02T03:04:05",
            "updated_at": "2026-01-02T03:04:05",
        },
    )
    db_session.commit()

    def fail_move(*args, **kwargs):
        raise OSError("simulated move failure")

    monkeypatch.setattr("app.services.note.shutil.move", fail_move)

    with pytest.raises(OSError):
        NoteService.migrate_old_data(db_session)

    assert old_file.read_text(encoding="utf-8") == "legacy content"
    assert db_session.query(NoteNode).filter(NoteNode.id == note_id).count() == 0
    assert inspect(db_session.bind).has_table("folders")
    assert inspect(db_session.bind).has_table("notes")


def test_startup_note_migration_restores_files_when_canonicalization_fails(
    db_session, monkeypatch, tmp_path
):
    from app import main as main_module

    Base.metadata.create_all(bind=db_session.bind)
    user = User(username="outer-rollback-user", email="outer@example.com", password_hash="hashed")
    db_session.add(user)
    db_session.flush()
    notebook = Notebook(user_id=user.id, name="Outer rollback notebook")
    db_session.add(notebook)
    db_session.commit()

    folder_id = uuid4()
    note_id = uuid4()
    notes_dir = tmp_path / "notes_data"
    old_file = notes_dir / str(user.id) / "legacy" / "legacy.md"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("legacy content", encoding="utf-8")
    monkeypatch.setattr("app.services.note.NOTES_DIR", notes_dir)
    _create_legacy_tables(db_session)
    db_session.execute(
        text("INSERT INTO folders (id, notebook_id, parent_id, name, path) VALUES (:id, :notebook_id, NULL, :name, :path)"),
        {"id": str(folder_id), "notebook_id": str(notebook.id), "name": "Legacy", "path": "/Legacy"},
    )
    db_session.execute(
        text(
            "INSERT INTO notes (id, folder_id, title, file_path, created_at, updated_at) "
            "VALUES (:id, :folder_id, :title, :file_path, :created_at, :updated_at)"
        ),
        {
            "id": str(note_id),
            "folder_id": str(folder_id),
            "title": "Legacy note",
            "file_path": str(old_file),
            "created_at": "2026-01-02T03:04:05",
            "updated_at": "2026-01-02T03:04:05",
        },
    )
    db_session.commit()

    monkeypatch.setattr(main_module, "engine", db_session.bind)

    def fail_canonicalization(_db):
        raise RuntimeError("simulated canonicalization failure")

    monkeypatch.setattr(main_module.NoteService, "canonicalize_existing_tags", fail_canonicalization)

    with pytest.raises(RuntimeError, match="simulated canonicalization failure"):
        main_module._migrate_note_data()

    new_file = notes_dir / str(user.id) / str(notebook.id) / "Legacy" / "Legacy note.md"
    assert old_file.read_text(encoding="utf-8") == "legacy content"
    assert not new_file.exists()
    assert db_session.query(NoteNode).filter(NoteNode.id == note_id).count() == 0
    assert inspect(db_session.bind).has_table("folders")
    assert inspect(db_session.bind).has_table("notes")


def test_startup_note_migration_restores_files_when_commit_fails(
    db_session, monkeypatch, tmp_path
):
    from app import main as main_module

    old_file = tmp_path / "legacy.md"
    new_file = tmp_path / "migrated" / "legacy.md"
    old_file.write_text("legacy content", encoding="utf-8")
    new_file.parent.mkdir()
    new_file.write_text(old_file.read_text(encoding="utf-8"), encoding="utf-8")
    old_file.unlink()

    monkeypatch.setattr(main_module, "engine", db_session.bind)
    monkeypatch.setattr(
        main_module.NoteService,
        "migrate_old_data",
        lambda _db: [(str(old_file), str(new_file))],
    )
    monkeypatch.setattr(
        main_module.NoteService,
        "canonicalize_existing_tags",
        lambda _db: None,
    )

    def fail_commit(_session):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(main_module.Session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        main_module._migrate_note_data()

    assert old_file.read_text(encoding="utf-8") == "legacy content"
    assert not new_file.exists()
