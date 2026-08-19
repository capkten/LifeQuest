# backend/tests/test_notes.py
import os
import sqlite3
from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.models.note_node import NoteNode

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


@pytest.fixture
def migration_database(monkeypatch, db_session):
    from app import main as main_module

    testing_engine = db_session.get_bind()
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=testing_engine
    )
    monkeypatch.setattr(main_module, "engine", testing_engine)
    monkeypatch.setattr(main_module, "SessionLocal", testing_session_local)
    db_session.execute(text("DROP TABLE IF EXISTS notes"))
    db_session.execute(text("DROP TABLE IF EXISTS folders"))
    db_session.commit()
    yield
    db_session.rollback()
    db_session.execute(text("DROP TABLE IF EXISTS notes"))
    db_session.execute(text("DROP TABLE IF EXISTS folders"))
    db_session.commit()


def _register_and_login(client):
    """Helper: register a user and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_notebook(client, headers, name="My Notebook"):
    response = client.post(
        "/api/notes/notebooks",
        json={"name": name},
        headers=headers,
    )
    return response.json()


def test_create_notebook(client):
    headers = _register_and_login(client)
    response = client.post(
        "/api/notes/notebooks",
        json={"name": "My Notebook", "description": "Test notebook"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Notebook"


def test_create_folder_at_root(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    response = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Project A"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Project A"
    assert data["type"] == "folder"
    assert data["parent_id"] is None


def test_create_note_at_root(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    response = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Inbox", "content": "# Hello"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Inbox"
    assert data["type"] == "note"


def test_create_nested_folders(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create root folder
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Project A"},
        headers=headers,
    )
    folder_id = r1.json()["id"]

    # Create subfolder
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Requirements", "parent_id": folder_id},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["parent_id"] == folder_id
    assert "/Project A/Requirements" in r2.json()["path"]


def test_create_note_in_subfolder(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create folder
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Docs"},
        headers=headers,
    )
    folder_id = r1.json()["id"]

    # Create note in folder
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Meeting Notes", "content": "## Notes", "parent_id": folder_id},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["type"] == "note"
    assert "/Docs/Meeting Notes.md" in r2.json()["path"]


def test_same_name_conflict_note_and_folder(client):
    """A note and folder with the same normalized name in the same dir should conflict."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create folder "test"
    client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "test"},
        headers=headers,
    )

    # Try to create note "test" at same level
    r = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "test", "content": ""},
        headers=headers,
    )
    assert r.status_code == 409
    assert "同名冲突" in r.json()["detail"]


def test_same_name_conflict_two_notes(client):
    """Two notes with the same name in the same directory should conflict."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Weekly", "content": "week 1"},
        headers=headers,
    )
    r = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Weekly", "content": "week 2"},
        headers=headers,
    )
    assert r.status_code == 409


def test_same_name_allowed_in_different_dirs(client):
    """Same name in different directories should succeed."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create two folders
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir A"},
        headers=headers,
    )
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir B"},
        headers=headers,
    )
    dir_a = r1.json()["id"]
    dir_b = r2.json()["id"]

    # Create note "report" in both
    n1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "A", "parent_id": dir_a},
        headers=headers,
    )
    n2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "B", "parent_id": dir_b},
        headers=headers,
    )
    assert n1.status_code == 200
    assert n2.status_code == 200


def test_rename_to_existing_name_returns_409(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Alpha", "content": ""},
        headers=headers,
    )
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Beta", "content": ""},
        headers=headers,
    )
    beta_id = r2.json()["id"]

    # Rename Beta -> Alpha should fail
    r = client.patch(
        f"/api/notes/nodes/{beta_id}",
        json={"name": "Alpha"},
        headers=headers,
    )
    assert r.status_code == 409


def test_move_to_dir_with_same_name_returns_409(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create two folders
    r1 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir A"},
        headers=headers,
    )
    r2 = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Dir B"},
        headers=headers,
    )
    dir_a = r1.json()["id"]
    dir_b = r2.json()["id"]

    # Create "report" in Dir A
    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "", "parent_id": dir_a},
        headers=headers,
    )
    # Create "report" in Dir B
    r_note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "report", "content": "", "parent_id": dir_b},
        headers=headers,
    )
    report_b_id = r_note.json()["id"]

    # Try to move report from Dir B to root (no conflict) — should succeed
    r = client.patch(
        f"/api/notes/nodes/{report_b_id}",
        json={"parent_id": None},
        headers=headers,
    )
    assert r.status_code == 200

    # But try to move it back to Dir A where "report" already exists
    r = client.patch(
        f"/api/notes/nodes/{report_b_id}",
        json={"parent_id": dir_a},
        headers=headers,
    )
    assert r.status_code == 409


def test_delete_folder_recursive(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    # Create folder with a note inside
    r_folder = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Temp"},
        headers=headers,
    )
    folder_id = r_folder.json()["id"]

    r_note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Doc", "content": "content here", "parent_id": folder_id},
        headers=headers,
    )
    note_id = r_note.json()["id"]

    # Delete the folder
    r = client.delete(f"/api/notes/nodes/{folder_id}", headers=headers)
    assert r.status_code == 200

    # Verify note is also gone
    r = client.get(f"/api/notes/{note_id}", headers=headers)
    assert r.status_code == 404


def test_get_tree(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Folder1"},
        headers=headers,
    )
    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Root Note", "content": ""},
        headers=headers,
    )

    r = client.get(f"/api/notes/notebooks/{nb['id']}/tree", headers=headers)
    assert r.status_code == 200
    tree = r.json()
    assert len(tree) == 2
    names = {n["name"] for n in tree}
    assert "Folder1" in names
    assert "Root Note" in names


def test_get_children(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    r_folder = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Folder1"},
        headers=headers,
    )
    folder_id = r_folder.json()["id"]

    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Note In Folder", "content": "", "parent_id": folder_id},
        headers=headers,
    )
    client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Root Note", "content": ""},
        headers=headers,
    )

    # Root children should have Folder1 and Root Note
    r = client.get(f"/api/notes/notebooks/{nb['id']}/children", headers=headers)
    assert r.status_code == 200
    children = r.json()
    assert len(children) == 2

    # Folder1 children should have Note In Folder
    r = client.get(
        f"/api/notes/notebooks/{nb['id']}/children?parent_id={folder_id}",
        headers=headers,
    )
    children = r.json()
    assert len(children) == 1
    assert children[0]["name"] == "Note In Folder"


def test_cannot_access_other_users_notebook(client):
    # User 1
    headers1 = _register_and_login(client)
    nb = _create_notebook(client, headers1)

    # User 2
    client.post(
        "/api/auth/register",
        json={"username": "user2", "email": "u2@e.com", "password": "pass123456"},
    )
    login2 = client.post(
        "/api/auth/login",
        data={"username": "user2", "password": "pass123456"},
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    # User 2 cannot see User 1's tree
    r = client.get(f"/api/notes/notebooks/{nb['id']}/tree", headers=headers2)
    assert r.status_code == 403


def test_file_path_stays_within_notes_data(client):
    """Names with path separators should be sanitized."""
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    r = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "../escape", "content": ""},
        headers=headers,
    )
    # The name should be rejected by normalize_name due to invalid chars
    assert r.status_code == 400


def test_create_note_rolls_back_when_markdown_write_fails(client, monkeypatch):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)

    from app.services import note as note_module

    def fail_write(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(note_module, "_write_content_atomically", fail_write)
    with pytest.raises(OSError):
        client.post(
            f"/api/notes/notebooks/{nb['id']}/notes",
            json={"title": "Unwritten", "content": "content"},
            headers=headers,
        )

    tree = client.get(f"/api/notes/notebooks/{nb['id']}/tree", headers=headers)
    assert tree.status_code == 200
    assert tree.json() == []


def test_open_note_updates_last_opened_at_and_returns_note_metadata(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)
    created = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Opened", "content": "hello"},
        headers=headers,
    ).json()

    response = client.post(f"/api/notes/{created['id']}/open", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["last_opened_at"] is not None

    detail = client.get(f"/api/notes/{created['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["last_opened_at"] == response.json()["last_opened_at"]


def test_recent_notes_are_sorted_by_last_opened_at(client):
    headers = _register_and_login(client)
    first_nb = _create_notebook(client, headers, "First Notebook")
    second_nb = _create_notebook(client, headers, "Second Notebook")
    first = client.post(
        f"/api/notes/notebooks/{first_nb['id']}/notes",
        json={"title": "First", "content": ""},
        headers=headers,
    ).json()
    second = client.post(
        f"/api/notes/notebooks/{second_nb['id']}/notes",
        json={"title": "Second", "content": ""},
        headers=headers,
    ).json()

    assert client.post(f"/api/notes/{first['id']}/open", headers=headers).status_code == 200
    assert client.post(f"/api/notes/{second['id']}/open", headers=headers).status_code == 200

    response = client.get("/api/notes/recent?limit=2", headers=headers)

    assert response.status_code == 200
    assert [note["id"] for note in response.json()] == [second["id"], first["id"]]
    assert {note["id"]: note["notebook_name"] for note in response.json()} == {
        second["id"]: "Second Notebook",
        first["id"]: "First Notebook",
    }


def test_recent_notes_are_isolated_and_other_user_cannot_open_note(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)
    note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Private", "content": ""},
        headers=headers,
    ).json()
    client.post(f"/api/notes/{note['id']}/open", headers=headers)

    client.post(
        "/api/auth/register",
        json={"username": "user2", "email": "u2@e.com", "password": "pass123456"},
    )
    login2 = client.post(
        "/api/auth/login",
        data={"username": "user2", "password": "pass123456"},
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    assert client.get("/api/notes/recent", headers=headers2).json() == []
    assert client.post(f"/api/notes/{note['id']}/open", headers=headers2).status_code == 403


def test_opening_folder_returns_not_found(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)
    folder = client.post(
        f"/api/notes/notebooks/{nb['id']}/folders",
        json={"name": "Folder"},
        headers=headers,
    ).json()

    response = client.post(f"/api/notes/{folder['id']}/open", headers=headers)

    assert response.status_code == 404


def test_recent_limit_must_be_between_one_and_fifty(client):
    headers = _register_and_login(client)

    response = client.get("/api/notes/recent?limit=51", headers=headers)

    assert response.status_code == 422


def test_open_note_returns_last_opened_at_as_utc(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)
    note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "UTC note", "content": ""},
        headers=headers,
    ).json()

    response = client.post(f"/api/notes/{note['id']}/open", headers=headers)

    assert response.status_code == 200
    opened_at = datetime.fromisoformat(response.json()["last_opened_at"])
    assert opened_at.tzinfo is not None
    assert opened_at.astimezone(timezone.utc).utcoffset() == timezone.utc.utcoffset(opened_at)


class _FakeMigrationInspector:
    def get_columns(self, table_name):
        columns = {
            "habits": ["last_completed_at"],
            "users": ["total_coins_earned"],
            "tasks": ["project_id", "phase_id", "milestone_id", "start_date", "priority", "sort_order"],
            "finance_transactions": ["recurring_id"],
            "note_nodes": [],
        }
        return [{"name": name} for name in columns[table_name]]


class _TribulationMigrationInspector(_FakeMigrationInspector):
    def get_columns(self, table_name):
        if table_name == "tribulation_attempts":
            return [{"name": "id"}, {"name": "user_id"}, {"name": "attempted_date"}, {"name": "attempted_at"}]
        return super().get_columns(table_name)


class _TribulationMigrationResult:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return list(self.rows)


class _TribulationMigrationConnection:
    def __init__(self):
        self.rows = [
            ("keep-latest", "user-1", "2026-08-17", "2026-08-17 18:00:00"),
            ("delete-older", "user-1", "2026-08-17", "2026-08-17 09:00:00"),
            ("keep-other-day", "user-1", "2026-08-16", "2026-08-16 09:00:00"),
        ]
        self.deleted = []
        self.statements = []

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append(sql)
        if sql.startswith("SELECT id, user_id, attempted_date, attempted_at"):
            return _TribulationMigrationResult(self.rows)
        if sql.startswith("DELETE FROM tribulation_attempts"):
            attempt_id = params["id"]
            self.rows = [row for row in self.rows if row[0] != attempt_id]
            self.deleted.append(attempt_id)
        return _TribulationMigrationResult([])


class _TribulationMigrationEngine:
    def __init__(self):
        self.connection = _TribulationMigrationConnection()

    def begin(self):
        connection = self.connection

        class _Context:
            def __enter__(self):
                return connection

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Context()


class _FakeMigrationConnection:
    def __init__(self, error, error_column="last_opened_at"):
        self.error = error
        self.error_column = error_column

    def execute(self, statement):
        if f"ADD COLUMN {self.error_column}" in str(statement):
            raise self.error
        class _Result:
            def fetchall(self):
                return []
        return _Result()


class _FakeBeginContext:
    def __init__(self, error, error_column="last_opened_at"):
        self.error = error
        self.error_column = error_column

    def __enter__(self):
        return _FakeMigrationConnection(self.error, self.error_column)

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeMigrationEngine:
    def __init__(self, error, error_column="last_opened_at"):
        self.error = error
        self.error_column = error_column

    def begin(self):
        return _FakeBeginContext(self.error, self.error_column)


def _run_migration_with_note_column_error(monkeypatch, error, error_column="last_opened_at", inspector=None):
    from app import main as main_module

    monkeypatch.setattr(main_module, "inspect", lambda engine: inspector or _FakeMigrationInspector())
    monkeypatch.setattr(main_module, "engine", _FakeMigrationEngine(error, error_column))
    return main_module._migrate_columns()


def test_migrate_columns_ignores_only_duplicate_last_opened_at_column(monkeypatch):
    duplicate_error = OperationalError(
        "ALTER TABLE note_nodes ADD COLUMN last_opened_at DATETIME",
        {},
        sqlite3.OperationalError("duplicate column name: last_opened_at"),
    )

    _run_migration_with_note_column_error(monkeypatch, duplicate_error)


def test_migrate_columns_propagates_non_duplicate_last_opened_at_error(monkeypatch):
    locked_error = OperationalError(
        "ALTER TABLE note_nodes ADD COLUMN last_opened_at DATETIME",
        {},
        sqlite3.OperationalError("database is locked"),
    )

    with pytest.raises(OperationalError, match="database is locked"):
        _run_migration_with_note_column_error(monkeypatch, locked_error)


def test_migrate_columns_ignores_only_duplicate_tags_normalized_column(monkeypatch):
    duplicate_error = OperationalError(
        "ALTER TABLE note_nodes ADD COLUMN tags_normalized BOOLEAN",
        {},
        sqlite3.OperationalError("duplicate column name: tags_normalized"),
    )

    class _Inspector(_FakeMigrationInspector):
        def get_columns(self, table_name):
            if table_name == "note_nodes":
                return [{"name": "last_opened_at"}]
            return super().get_columns(table_name)

    _run_migration_with_note_column_error(
        monkeypatch, duplicate_error, "tags_normalized", _Inspector()
    )


def test_migrate_columns_does_not_canonicalize_before_old_note_migration(monkeypatch):
    from app import main as main_module

    class _Connection:
        def __init__(self):
            self.statements = []

        def execute(self, statement, params=None):
            self.statements.append(str(statement))

    class _Engine:
        def __init__(self):
            self.connection = _Connection()

        def begin(self):
            connection = self.connection

            class _Context:
                def __enter__(self):
                    return connection

                def __exit__(self, exc_type, exc, tb):
                    return False

            return _Context()

    engine = _Engine()
    monkeypatch.setattr(main_module, "inspect", lambda engine: _FakeMigrationInspector())
    monkeypatch.setattr(main_module, "engine", engine)

    main_module._migrate_columns()

    assert not any("SELECT id, tags" in statement for statement in engine.connection.statements)


def test_migrate_columns_deduplicates_daily_tribulation_attempts_before_unique_index(monkeypatch):
    from app import main as main_module

    engine = _TribulationMigrationEngine()
    monkeypatch.setattr(main_module, "inspect", lambda engine: _TribulationMigrationInspector())
    monkeypatch.setattr(main_module, "engine", engine)

    main_module._migrate_columns()
    main_module._migrate_columns()

    assert engine.connection.deleted == ["delete-older"]
    index_position = next(
        index for index, statement in enumerate(engine.connection.statements)
        if "CREATE UNIQUE INDEX" in statement
    )
    delete_position = next(
        index for index, statement in enumerate(engine.connection.statements)
        if "DELETE FROM tribulation_attempts" in statement
    )
    assert delete_position < index_position


def test_legacy_note_migration_canonicalizes_tags_for_discover(migration_database, client, db_session):
    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers, "Migrated Tags")
    folder_id = "00000000-0000-0000-0000-000000000101"
    note_id = "00000000-0000-0000-0000-000000000102"

    db_session.execute(text(
        "CREATE TABLE folders ("
        "id VARCHAR(36) PRIMARY KEY, notebook_id VARCHAR(36) NOT NULL, "
        "parent_id VARCHAR(36), name VARCHAR(200) NOT NULL, path VARCHAR(1000) NOT NULL)"
    ))
    db_session.execute(text(
        "CREATE TABLE notes ("
        "id VARCHAR(36) PRIMARY KEY, folder_id VARCHAR(36) NOT NULL, "
        "title VARCHAR(200) NOT NULL, file_path VARCHAR(1000), summary TEXT, "
        "tags VARCHAR(500), is_pinned BOOLEAN, word_count INTEGER, "
        "created_at DATETIME, updated_at DATETIME)"
    ))
    db_session.execute(text(
        "INSERT INTO folders (id, notebook_id, name, path) "
        "VALUES (:id, :notebook_id, :name, :path)"
    ), {"id": folder_id, "notebook_id": notebook["id"], "name": "Legacy", "path": "/Legacy"})
    db_session.execute(text(
        "INSERT INTO notes (id, folder_id, title, tags) "
        "VALUES (:id, :folder_id, :title, :tags)"
    ), {"id": note_id, "folder_id": folder_id, "title": "Python", "tags": "work, python"})
    db_session.commit()

    from app.services.note import NoteService
    NoteService.migrate_old_data(db_session)
    db_session.commit()

    migrated_node = db_session.get(NoteNode, UUID(note_id))
    assert migrated_node.tags_normalized is True

    response = client.get(
        "/api/notes/discover", params={"tag": "python"}, headers=headers
    )

    assert response.status_code == 200
    assert [note["id"] for note in response.json()] == [note_id]
    assert response.json()[0]["tags"] == "work,python"


def test_migrate_old_data_leaves_commit_to_outer_transaction(migration_database, client, db_session, monkeypatch):
    from app.services.note import NoteService

    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers, "Migration transaction")
    folder_id = "00000000-0000-0000-0000-000000000103"
    note_id = "00000000-0000-0000-0000-000000000104"
    db_session.execute(text(
        "CREATE TABLE folders ("
        "id VARCHAR(36) PRIMARY KEY, notebook_id VARCHAR(36) NOT NULL, "
        "parent_id VARCHAR(36), name VARCHAR(200) NOT NULL, path VARCHAR(1000) NOT NULL)"
    ))
    db_session.execute(text(
        "CREATE TABLE notes ("
        "id VARCHAR(36) PRIMARY KEY, folder_id VARCHAR(36) NOT NULL, "
        "title VARCHAR(200) NOT NULL, file_path VARCHAR(1000), summary TEXT, "
        "tags VARCHAR(500), is_pinned BOOLEAN, word_count INTEGER, "
        "created_at DATETIME, updated_at DATETIME)"
    ))
    db_session.execute(text(
        "INSERT INTO folders (id, notebook_id, name, path) "
        "VALUES (:id, :notebook_id, :name, :path)"
    ), {"id": folder_id, "notebook_id": notebook["id"], "name": "Legacy", "path": "/Legacy"})
    db_session.execute(text(
        "INSERT INTO notes (id, folder_id, title, tags) "
        "VALUES (:id, :folder_id, :title, :tags)"
    ), {"id": note_id, "folder_id": folder_id, "title": "Atomic", "tags": "work"})
    db_session.commit()

    def unexpected_commit():
        raise AssertionError("migrate_old_data must not commit")

    with monkeypatch.context() as patch:
        patch.setattr(db_session, "commit", unexpected_commit)
        NoteService.migrate_old_data(db_session)

    db_session.commit()


def test_canonicalize_existing_tags_normalizes_legacy_tokens_once(client, db_session):
    from app.services.note import NoteService

    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers, "Legacy Canonicalization")
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Legacy", "content": "", "tags": "placeholder"},
        headers=headers,
    ).json()
    node = db_session.get(NoteNode, UUID(note["id"]))
    node.tags = "work,   python,\t,  personal  ,"
    node.tags_normalized = None
    db_session.commit()

    NoteService.canonicalize_existing_tags(db_session.connection())
    db_session.commit()

    assert node.tags == "work,python,personal"
    assert node.tags_normalized is True


def test_canonicalize_existing_tags_update_requires_unmarked_row(client, db_session):
    from app.services.note import NoteService

    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers, "Concurrent canonicalization")
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Concurrent", "content": "", "tags": "placeholder"},
        headers=headers,
    ).json()
    node = db_session.get(NoteNode, UUID(note["id"]))
    node.tags = "work,   python"
    node.tags_normalized = None
    db_session.commit()

    class _SnapshotThenMarkedDb:
        def __init__(self, connection):
            self.connection = connection
            self.update_statement = None
            self.marked_by_other_worker = False

        def execute(self, statement, params=None):
                if "SELECT id, tags" in str(statement):
                    rows = self.connection.execute(statement, params).fetchall()
                    self.marked_by_other_worker = True
                    return type("_Rows", (), {"fetchall": lambda self: rows})()
                self.update_statement = str(statement)
                if self.marked_by_other_worker:
                    return type("_Result", (), {})()
                return self.connection.execute(statement, params)

    db = _SnapshotThenMarkedDb(db_session.connection())
    NoteService.canonicalize_existing_tags(db)
    db_session.commit()

    assert "TAGS_NORMALIZED IS NULL" in db.update_statement.upper()
    assert node.tags == "work,   python"
    assert node.tags_normalized is None


def test_canonicalize_existing_tags_skips_already_normalized_rows(client, db_session):
    from sqlalchemy import event
    from app.services.note import NoteService

    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers, "Idempotent Canonicalization")
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Already normalized", "content": "", "tags": "work"},
        headers=headers,
    ).json()
    node = db_session.get(NoteNode, UUID(note["id"]))
    assert node.tags_normalized is True
    db_session.commit()

    statements = []
    connection = db_session.get_bind()
    listener = lambda conn, cursor, statement, parameters, context, executemany: statements.append(statement)
    event.listen(connection, "before_cursor_execute", listener)
    try:
        NoteService.canonicalize_existing_tags(db_session.connection())
        db_session.commit()
    finally:
        event.remove(connection, "before_cursor_execute", listener)

    assert not any("UPDATE note_nodes" in statement.upper() for statement in statements)
    assert any("tags_normalized" in statement.lower() and "IS NULL" in statement.upper() for statement in statements)


def test_recent_limit_accepts_zero_one_and_fifty_boundaries(client):
    headers = _register_and_login(client)

    assert client.get("/api/notes/recent?limit=0", headers=headers).status_code == 422
    assert client.get("/api/notes/recent?limit=1", headers=headers).status_code == 200
    assert client.get("/api/notes/recent?limit=50", headers=headers).status_code == 200


def test_recent_notes_use_updated_at_as_tie_breaker(client, db_session):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)
    first = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "First tie", "content": ""},
        headers=headers,
    ).json()
    second = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Second tie", "content": ""},
        headers=headers,
    ).json()

    opened_at = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    older = datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 1, 1, 12, 2, tzinfo=timezone.utc)
    for note_id, updated_at in ((first["id"], older), (second["id"], newer)):
        node = db_session.get(NoteNode, UUID(note_id))
        node.last_opened_at = opened_at
        node.updated_at = updated_at
    db_session.commit()

    response = client.get("/api/notes/recent?limit=2", headers=headers)

    assert response.status_code == 200
    assert [note["id"] for note in response.json()] == [second["id"], first["id"]]


def test_discover_notes_supports_title_updated_and_recent_sorting(client, db_session):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers, "Discovery Notebook")
    created = {}
    for title in ("Zeta", "Alpha", "Middle"):
        created[title] = client.post(
            f"/api/notes/notebooks/{nb['id']}/notes",
            json={"title": title, "content": title},
            headers=headers,
        ).json()

    timestamps = {
        "Zeta": datetime(2026, 1, 3, tzinfo=timezone.utc),
        "Alpha": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "Middle": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }
    opened = {
        "Zeta": datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
        "Alpha": datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
        "Middle": datetime(2026, 1, 1, 9, tzinfo=timezone.utc),
    }
    for title, payload in created.items():
        node = db_session.get(NoteNode, UUID(payload["id"]))
        node.created_at = timestamps[title]
        node.updated_at = timestamps[title]
        node.last_opened_at = opened[title]
    db_session.commit()

    assert [n["name"] for n in client.get(
        "/api/notes/discover?sort=title", headers=headers
    ).json()] == ["Alpha", "Middle", "Zeta"]
    assert [n["name"] for n in client.get(
        "/api/notes/discover?sort=updated", headers=headers
    ).json()] == ["Zeta", "Middle", "Alpha"]
    assert [n["name"] for n in client.get(
        "/api/notes/discover?sort=last_opened", headers=headers
    ).json()] == ["Alpha", "Middle", "Zeta"]


def test_discover_created_and_updated_sorts_put_nulls_last(client, db_session):
    from app.repositories.note import NoteNodeRepository

    headers = _register_and_login(client)
    nb = _create_notebook(client, headers, "NULL sort notebook")
    created = {}
    for title in ("Created null", "Updated null", "Both timestamps"):
        created[title] = client.post(
            f"/api/notes/notebooks/{nb['id']}/notes",
            json={"title": title, "content": title},
            headers=headers,
        ).json()

    nodes = {title: db_session.get(NoteNode, UUID(payload["id"])) for title, payload in created.items()}
    nodes["Created null"].created_at = None
    nodes["Created null"].updated_at = datetime(2026, 1, 3, tzinfo=timezone.utc)
    nodes["Updated null"].created_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    nodes["Updated null"].updated_at = None
    nodes["Both timestamps"].created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    nodes["Both timestamps"].updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db_session.commit()

    statements = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    connection = db_session.connection()
    event.listen(connection, "before_cursor_execute", capture)
    try:
        repository = NoteNodeRepository(db_session)
        assert [node.name for node in repository.discover(
            UUID(nb["user_id"]), "created", notebook_id=UUID(nb["id"])
        )] == ["Updated null", "Both timestamps", "Created null"]
        assert [node.name for node in repository.discover(
            UUID(nb["user_id"]), "updated", notebook_id=UUID(nb["id"])
        )] == ["Created null", "Both timestamps", "Updated null"]
    finally:
        event.remove(connection, "before_cursor_execute", capture)

    assert any("created_at DESC NULLS LAST" in statement for statement in statements)
    assert any("updated_at DESC NULLS LAST" in statement for statement in statements)


def test_discover_notes_filters_pinned_tag_notebook_and_updated_range(client, db_session):
    headers = _register_and_login(client)
    first_nb = _create_notebook(client, headers, "First Notebook")
    second_nb = _create_notebook(client, headers, "Second Notebook")
    first = client.post(
        f"/api/notes/notebooks/{first_nb['id']}/notes",
        json={"title": "Pinned Python", "content": "one two", "tags": "python,work", "is_pinned": True},
        headers=headers,
    ).json()
    client.put(
        f"/api/notes/{first['id']}",
        json={"is_pinned": True},
        headers=headers,
    )
    second = client.post(
        f"/api/notes/notebooks/{second_nb['id']}/notes",
        json={"title": "Plain Python", "content": "one", "tags": "python"},
        headers=headers,
    ).json()
    third = client.post(
        f"/api/notes/notebooks/{first_nb['id']}/notes",
        json={"title": "Old Work", "content": "one", "tags": "work"},
        headers=headers,
    ).json()
    for note_id, updated_at in (
        (first["id"], datetime(2026, 2, 10, tzinfo=timezone.utc)),
        (second["id"], datetime(2026, 2, 11, tzinfo=timezone.utc)),
        (third["id"], datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ):
        db_session.get(NoteNode, UUID(note_id)).updated_at = updated_at
    db_session.commit()

    response = client.get(
        "/api/notes/discover",
        params={
            "notebook_id": first_nb["id"],
            "tag": "python",
            "pinned": "true",
            "updated_after": "2026-02-01T00:00:00Z",
            "updated_before": "2026-02-20T00:00:00Z",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert [note["id"] for note in response.json()] == [first["id"]]
    assert response.json()[0]["notebook_name"] == "First Notebook"
    assert response.json()[0]["path"] == "/Pinned Python.md"
    assert response.json()[0]["word_count"] == 2
    assert response.json()[0]["tags"] == "python,work"
    assert response.json()[0]["is_pinned"] is True


def test_discover_notes_matches_exact_tag_tokens(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers, "Tag Matching Notebook")

    matching_tags = {
        "tag itself": "python",
        "tag before comma": "python,work",
        "tag after comma": "work,python",
        "tag with spaces": "work, python, personal",
    }
    matching_ids = []
    for title, tags in matching_tags.items():
        note = client.post(
            f"/api/notes/notebooks/{nb['id']}/notes",
            json={"title": title, "content": title, "tags": tags},
            headers=headers,
        ).json()
        matching_ids.append(note["id"])

    non_matching_ids = []
    for title, tags in (("python3", "python3"), ("cpython", "cpython")):
        note = client.post(
            f"/api/notes/notebooks/{nb['id']}/notes",
            json={"title": title, "content": title, "tags": tags},
            headers=headers,
        ).json()
        non_matching_ids.append(note["id"])

    response = client.get(
        "/api/notes/discover",
        params={"tag": "python"},
        headers=headers,
    )

    assert response.status_code == 200
    result_ids = {note["id"] for note in response.json()}
    assert result_ids == set(matching_ids)
    assert not result_ids.intersection(non_matching_ids)


def test_discover_tag_filter_applies_limit_in_database(monkeypatch):
    from app.repositories.note import NoteNodeRepository

    class _Query:
        def __init__(self):
            self.all_called = False
            self.limit_value = None

        def join(self, *args):
            return self

        def filter(self, *args):
            return self

        def order_by(self, *args):
            return self

        def limit(self, value):
            self.limit_value = value
            return self

        def all(self):
            self.all_called = True
            if self.limit_value is None:
                raise AssertionError("tag discovery must not load an unbounded query")
            return []

    query = _Query()

    class _DB:
        def query(self, *args):
            return query

    result = NoteNodeRepository(_DB()).discover(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        sort="updated",
        tag="python",
        limit=3,
    )

    assert result == []
    assert query.limit_value == 3


def test_create_and_update_notes_canonicalize_tag_tokens(client, db_session):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers, "Canonical Tags")

    created = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Created", "content": "", "tags": " python,  work\t"},
        headers=headers,
    )

    assert created.status_code == 200
    assert created.json()["tags"] == "python,work"
    assert db_session.get(NoteNode, UUID(created.json()["id"])).tags_normalized is True

    updated = client.put(
        f"/api/notes/{created.json()['id']}",
        json={"tags": "  work,\tpython  "},
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["tags"] == "work,python"
    assert db_session.get(NoteNode, UUID(created.json()["id"])).tags_normalized is True


def test_discover_tag_filter_handles_legacy_whitespace_and_empty_input(client, db_session):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers, "Legacy Tags")
    notes = {}
    for title, tags in {
        "spaces": "work,  python",
        "tab": "work,\tpython",
        "leading": "  python,work  ",
        "python3": "python3",
        "cpython": "cpython",
    }.items():
        response = client.post(
            f"/api/notes/notebooks/{nb['id']}/notes",
            json={"title": title, "content": "", "tags": "placeholder"},
            headers=headers,
        )
        assert response.status_code == 200
        note = response.json()
        notes[title] = note["id"]
        node = db_session.get(NoteNode, UUID(note["id"]))
        node.tags = tags
        node.tags_normalized = None
    db_session.commit()

    from app.services.note import NoteService
    NoteService.canonicalize_existing_tags(db_session.connection())
    db_session.commit()
    NoteService.canonicalize_existing_tags(db_session.connection())
    db_session.commit()

    matching = client.get(
        "/api/notes/discover", params={"tag": "  python  "}, headers=headers
    )
    empty = client.get(
        "/api/notes/discover", params={"tag": " \t "}, headers=headers
    )

    assert matching.status_code == 200
    assert {note["id"] for note in matching.json()} == {
        notes["spaces"], notes["tab"], notes["leading"]
    }
    assert empty.status_code == 200
    assert empty.json() == []


def test_discover_notes_isolates_users_and_rejects_unknown_sort(client):
    headers = _register_and_login(client)
    nb = _create_notebook(client, headers)
    note = client.post(
        f"/api/notes/notebooks/{nb['id']}/notes",
        json={"title": "Private discovery", "content": "secret"},
        headers=headers,
    ).json()

    client.post(
        "/api/auth/register",
        json={"username": "user2", "email": "u2@e.com", "password": "pass123456"},
    )
    login2 = client.post(
        "/api/auth/login",
        data={"username": "user2", "password": "pass123456"},
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    assert client.get("/api/notes/discover", headers=headers2).json() == []
    assert client.get(
        "/api/notes/discover?sort=unknown", headers=headers
    ).status_code == 422
    assert client.get(
        f"/api/notes/discover?notebook_id={nb['id']}", headers=headers2
    ).json() == []
