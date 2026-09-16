# backend/tests/test_notes.py
import os
import sqlite3
import multiprocessing
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.models.note_node import NoteNode

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


def _run_independent_tree_rename(
    database_url,
    notes_root,
    node_id,
    new_name,
    started,
    planned,
    result_queue,
    staged=None,
    resume=None,
):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.services import note as note_module
    from app.services.note import NoteService

    engine = create_engine(database_url, connect_args={"timeout": 30})
    session = sessionmaker(bind=engine, autoflush=False)()
    note_module.NOTES_DIR = Path(notes_root)
    service = NoteService(session)

    if planned is not None:
        original_plan = service._plan_tree_move

        def signal_after_plan(*args, **kwargs):
            result = original_plan(*args, **kwargs)
            planned.set()
            return result

        service._plan_tree_move = signal_after_plan

    if staged is not None:
        original_rename = Path.rename
        paused = False

        def pause_after_staging(path, target):
            nonlocal paused
            result = original_rename(path, target)
            if not paused:
                paused = True
                staged.set()
                if not resume.wait(15):
                    raise TimeoutError("tree move pause was not released")
            return result

        Path.rename = pause_after_staging

    started.set()
    try:
        node = service.rename_node(UUID(node_id), new_name)
        result_queue.put((new_name, "ok", node.path))
    except Exception as exc:
        result_queue.put((new_name, "error", repr(exc)))
    finally:
        session.close()
        engine.dispose()


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


def _create_nested_note_tree(client, headers):
    notebook = _create_notebook(client, headers, "Nested notebook")
    root = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "旧目录"},
        headers=headers,
    ).json()
    child = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "子目录", "parent_id": root["id"]},
        headers=headers,
    ).json()
    first_note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "第一篇", "content": "first", "parent_id": child["id"]},
        headers=headers,
    ).json()
    second_note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "第二篇", "content": "second", "parent_id": child["id"]},
        headers=headers,
    ).json()
    destination = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "目标目录"},
        headers=headers,
    ).json()
    return {
        "notebook": notebook,
        "root": root,
        "child": child,
        "notes": [first_note, second_note],
        "destination": destination,
    }


def _get_node(client, node_id, headers):
    response = client.get(f"/api/notes/{node_id}", headers=headers)
    assert response.status_code == 200
    return response.json()


def _snapshot_tree(client, tree, headers):
    nodes = [tree["root"], tree["child"], *tree["notes"], tree["destination"]]
    snapshot = []
    for node in nodes:
        if node["type"] == "note":
            current = _get_node(client, node["id"], headers)
            content = Path(current["content_path"]).read_text(encoding="utf-8")
            snapshot.append((current["id"], current["parent_id"], current["path"], current["content_path"], content))
        else:
            snapshot.append((node["id"], node["parent_id"], node["path"], node.get("content_path")))
    return snapshot


def test_renaming_folder_updates_descendant_db_and_files(client):
    headers = _register_and_login(client)
    tree = _create_nested_note_tree(client, headers)
    old_files = [Path(_get_node(client, note["id"], headers)["content_path"]) for note in tree["notes"]]
    expected_paths = [
        "/新目录/子目录/第一篇.md",
        "/新目录/子目录/第二篇.md",
    ]
    expected_content = ["first", "second"]

    response = client.patch(
        f"/api/notes/nodes/{tree['root']['id']}",
        json={"name": "新目录"},
        headers=headers,
    )

    assert response.status_code == 200
    moved_root = next(
        item for item in client.get(
            f"/api/notes/notebooks/{tree['notebook']['id']}/children",
            headers=headers,
        ).json()
        if item["id"] == tree["root"]["id"]
    )
    moved_child = next(
        item for item in client.get(
            f"/api/notes/notebooks/{tree['notebook']['id']}/children",
            params={"parent_id": tree["root"]["id"]},
            headers=headers,
        ).json()
        if item["id"] == tree["child"]["id"]
    )
    assert moved_root["id"] == tree["root"]["id"]
    assert moved_root["path"] == "/新目录"
    assert moved_child["id"] == tree["child"]["id"]
    assert moved_child["path"] == "/新目录/子目录"
    for old_file, note, expected_path, content in zip(old_files, tree["notes"], expected_paths, expected_content):
        refreshed = _get_node(client, note["id"], headers)
        assert refreshed["path"] == expected_path
        assert Path(refreshed["content_path"]).exists()
        assert refreshed["id"] == note["id"]
        assert refreshed["content"] == content
        assert not old_file.exists()


def test_note_tree_move_cleans_old_and_creates_new_directories(client):
    headers = _register_and_login(client)
    tree = _create_nested_note_tree(client, headers)
    old_note = _get_node(client, tree["notes"][0]["id"], headers)
    old_root_directory = Path(old_note["content_path"]).parents[1]
    new_root_directory = old_root_directory.parent / "目标目录" / "旧目录"

    response = client.patch(
        f"/api/notes/nodes/{tree['root']['id']}",
        json={"parent_id": tree["destination"]["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert not old_root_directory.exists()
    assert new_root_directory.is_dir()


def test_note_tree_renames_serialize_across_processes_with_sqlite(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.database import Base
    from app.models.note import Notebook
    from app.models.user import User

    database_path = tmp_path / "shared-notes.sqlite"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url, connect_args={"timeout": 30})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    user_id = uuid4()
    notebook_id = uuid4()
    folder_id = uuid4()
    note_id = uuid4()
    user = User(
        id=user_id,
        username=f"note-race-{uuid4().hex}",
        email=f"note-race-{uuid4().hex}@example.com",
        password_hash="unused",
    )
    notebook = Notebook(id=notebook_id, user_id=user.id, name="Concurrent notebook")
    folder = NoteNode(
        id=folder_id,
        notebook_id=notebook.id,
        type="folder",
        name="Original",
        normalized_name="original",
        path="/Original",
    )
    note = NoteNode(
        id=note_id,
        notebook_id=notebook.id,
        parent_id=folder.id,
        type="note",
        name="Document",
        normalized_name="document",
        path="/Original/Document.md",
        content_path=str(
            tmp_path / "notes" / str(user.id) / str(notebook.id) / "Original" / "Document.md"
        ),
    )
    session.add_all([user, notebook, folder, note])
    session.commit()
    initial_content_path = Path(note.content_path)
    initial_content_path.parent.mkdir(parents=True)
    initial_content_path.write_text("stable content", encoding="utf-8")
    session.close()
    engine.dispose()

    context = multiprocessing.get_context("fork")
    staged = context.Event()
    resume = context.Event()
    first_started = context.Event()
    second_started = context.Event()
    second_planned = context.Event()
    result_queue = context.Queue()
    first = context.Process(
        target=_run_independent_tree_rename,
        args=(
            database_url,
            str(tmp_path / "notes"),
            str(folder_id),
            "First rename",
            first_started,
            None,
            result_queue,
            staged,
            resume,
        ),
    )
    second = context.Process(
        target=_run_independent_tree_rename,
        args=(
            database_url,
            str(tmp_path / "notes"),
            str(folder_id),
            "Second rename",
            second_started,
            second_planned,
            result_queue,
        ),
    )

    first.start()
    try:
        assert first_started.wait(5), "first process did not enter the move service"
        if not staged.wait(10):
            first.join(1)
            detail = result_queue.get(timeout=2) if not first.is_alive() else "worker still running"
            pytest.fail(f"first process did not stage the note file: {detail}")
        second.start()
        assert second_started.wait(5)
        assert not second_planned.wait(0.5), "second process planned before acquiring the notebook lock"
    finally:
        resume.set()
        first.join(15)
        if second.pid is not None:
            second.join(15)
        for process in (first, second):
            if process.is_alive():
                process.terminate()
                process.join(5)

    results = [result_queue.get(timeout=2), result_queue.get(timeout=2)]
    results_by_process = {result[0]: result[1:] for result in results}
    assert first.exitcode == second.exitcode == 0
    assert results_by_process["First rename"] == ("ok", "/First rename")
    assert results_by_process["Second rename"] == ("ok", "/Second rename")

    verify_engine = create_engine(database_url)
    verify = sessionmaker(bind=verify_engine)()
    try:
        moved_folder = verify.query(NoteNode).filter_by(id=folder_id).one()
        moved_note = verify.query(NoteNode).filter_by(id=note_id).one()
        expected_file = tmp_path / "notes" / str(user_id) / str(notebook_id) / "Second rename" / "Document.md"
        assert moved_folder.path == "/Second rename"
        assert moved_note.path == "/Second rename/Document.md"
        assert Path(moved_note.content_path) == expected_file
        assert expected_file.read_text(encoding="utf-8") == "stable content"
    finally:
        verify.close()
        verify_engine.dispose()


def test_note_tree_move_restores_db_and_files_when_rename_fails(client, monkeypatch):
    headers = _register_and_login(client)
    tree = _create_nested_note_tree(client, headers)
    before = _snapshot_tree(client, tree, headers)
    old_note = _get_node(client, tree["notes"][0]["id"], headers)
    old_root_directory = Path(old_note["content_path"]).parents[1]
    new_root_directory = old_root_directory.parent / "目标目录" / "旧目录"
    original_rename = Path.rename
    rename_count = 0

    def fail_on_second_rename(path, target):
        nonlocal rename_count
        rename_count += 1
        if rename_count == 2:
            raise OSError("disk failure")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_on_second_rename)
    response = client.patch(
        f"/api/notes/nodes/{tree['root']['id']}",
        json={"parent_id": tree["destination"]["id"]},
        headers=headers,
    )

    assert response.status_code == 500
    assert _snapshot_tree(client, tree, headers) == before
    assert old_root_directory.is_dir()
    assert not new_root_directory.exists()
    assert not new_root_directory.parent.exists()


def test_note_tree_move_restores_db_and_files_when_refresh_fails(client, monkeypatch):
    from sqlalchemy.orm import Session

    headers = _register_and_login(client)
    tree = _create_nested_note_tree(client, headers)
    before = _snapshot_tree(client, tree, headers)
    original_refresh = Session.refresh

    def fail_refresh(session, instance, *args, **kwargs):
        if str(getattr(instance, "id", "")) == tree["root"]["id"]:
            raise OSError("refresh failure")
        return original_refresh(session, instance, *args, **kwargs)

    monkeypatch.setattr(Session, "refresh", fail_refresh)
    response = client.patch(
        f"/api/notes/nodes/{tree['root']['id']}",
        json={"parent_id": tree["destination"]["id"]},
        headers=headers,
    )

    assert response.status_code == 500
    assert _snapshot_tree(client, tree, headers) == before


def test_note_tree_move_restores_db_and_files_when_commit_fails(client, monkeypatch):
    from sqlalchemy.orm import Session

    headers = _register_and_login(client)
    tree = _create_nested_note_tree(client, headers)
    before = _snapshot_tree(client, tree, headers)

    def fail_commit(session, *args, **kwargs):
        raise OSError("commit failure")

    monkeypatch.setattr(Session, "commit", fail_commit)
    response = client.patch(
        f"/api/notes/nodes/{tree['root']['id']}",
        json={"parent_id": tree["destination"]["id"]},
        headers=headers,
    )

    assert response.status_code == 500
    assert _snapshot_tree(client, tree, headers) == before


def test_note_tree_move_keeps_files_when_commit_already_persisted_with_active_marker(client, monkeypatch):
    from sqlalchemy.orm import Session

    headers = _register_and_login(client)
    tree = _create_nested_note_tree(client, headers)
    original_commit = Session.commit
    original_in_transaction = Session.in_transaction

    def commit_then_fail(session, *args, **kwargs):
        original_commit(session, *args, **kwargs)
        session._post_commit_transaction_marker = True
        raise OSError("post-commit failure")

    def in_transaction_with_marker(session):
        if getattr(session, "_post_commit_transaction_marker", False):
            return True
        return original_in_transaction(session)

    monkeypatch.setattr(Session, "commit", commit_then_fail)
    monkeypatch.setattr(Session, "in_transaction", in_transaction_with_marker)
    response = client.patch(
        f"/api/notes/nodes/{tree['root']['id']}",
        json={"parent_id": tree["destination"]["id"]},
        headers=headers,
    )

    assert response.status_code == 500
    moved_note = _get_node(client, tree["notes"][0]["id"], headers)
    assert moved_note["path"] == "/目标目录/旧目录/子目录/第一篇.md"
    assert moved_note["content"] == "first"
    assert Path(moved_note["content_path"]).is_file()
    assert not Path(tree["notes"][0]["content_path"]).exists()


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
            ("delete-older", "user-1", "2026-08-17", "2026-08-17 17:00:00"),
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
