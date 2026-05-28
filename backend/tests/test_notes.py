# backend/tests/test_notes.py
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


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
