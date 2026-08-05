from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text

from app.models.note import Notebook
from app.models.note_node import NoteNode
from app.models.user import User
from app.database import Base
from app.services.note import NoteService


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
