import base64


def _register_and_login(client, username, email):
    client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "pass123456"},
    )
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "pass123456"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_note(client, headers):
    notebook = client.post(
        "/api/notes/notebooks",
        json={"name": "Shared notebook"},
        headers=headers,
    ).json()
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Shared note", "content": "initial"},
        headers=headers,
    ).json()
    return notebook, note


def test_shared_notebook_roles_and_revocation(client):
    owner_headers = _register_and_login(client, "share-owner", "share-owner@example.com")
    editor_headers = _register_and_login(client, "share-editor", "share-editor@example.com")
    viewer_headers = _register_and_login(client, "share-viewer", "share-viewer@example.com")
    notebook, note = _create_note(client, owner_headers)

    add_editor = client.post(
        f"/api/notes/notebooks/{notebook['id']}/members",
        json={"username_or_email": "share-editor", "role": "editor"},
        headers=owner_headers,
    )
    add_viewer = client.post(
        f"/api/notes/notebooks/{notebook['id']}/members",
        json={"username_or_email": "share-viewer@example.com", "role": "viewer"},
        headers=owner_headers,
    )
    assert add_editor.status_code == 200
    assert add_viewer.status_code == 200

    editor_notebooks = client.get("/api/notes/notebooks", headers=editor_headers).json()
    assert [(book["id"], book["role"], book["is_owner"]) for book in editor_notebooks] == [
        (notebook["id"], "editor", False)
    ]
    viewer_notebooks = client.get("/api/notes/notebooks", headers=viewer_headers).json()
    assert viewer_notebooks[0]["role"] == "viewer"

    editor_note = client.get(f"/api/notes/{note['id']}", headers=editor_headers)
    viewer_note = client.get(f"/api/notes/{note['id']}", headers=viewer_headers)
    assert editor_note.status_code == 200
    assert editor_note.json()["can_edit"] is True
    assert editor_note.json()["permission_role"] == "editor"
    assert viewer_note.status_code == 200
    assert viewer_note.json()["can_edit"] is False
    assert viewer_note.json()["permission_role"] == "viewer"

    editor_update = client.put(
        f"/api/notes/{note['id']}",
        json={"content": "edited by collaborator", "base_revision": 1},
        headers=editor_headers,
    )
    assert editor_update.status_code == 200
    current_revision = editor_update.json()["content_revision"]
    assert current_revision == 2

    viewer_update = client.put(
        f"/api/notes/{note['id']}",
        json={"content": "viewer must not write", "base_revision": current_revision},
        headers=viewer_headers,
    )
    assert viewer_update.status_code == 403

    viewer_create = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "blocked"},
        headers=viewer_headers,
    )
    assert viewer_create.status_code == 403

    stale_owner_update = client.put(
        f"/api/notes/{note['id']}",
        json={"summary": "stale metadata", "base_revision": 1},
        headers=owner_headers,
    )
    assert stale_owner_update.status_code == 409
    assert stale_owner_update.json()["detail"]["code"] == "NOTE_CONFLICT"

    remove_editor = client.delete(
        f"/api/notes/notebooks/{notebook['id']}/members/{add_editor.json()['user_id']}",
        headers=owner_headers,
    )
    assert remove_editor.status_code == 200
    assert client.get(f"/api/notes/{note['id']}", headers=editor_headers).status_code == 403


def test_note_attachments_require_note_access(client):
    owner_headers = _register_and_login(client, "attachment-owner", "attachment-owner@example.com")
    other_headers = _register_and_login(client, "attachment-other", "attachment-other@example.com")
    notebook, note = _create_note(client, owner_headers)

    upload = client.post(
        "/api/notes/upload-image",
        data={"note_id": note["id"]},
        files={"file": ("diagram.png", b"fake-image", "image/png")},
        headers=owner_headers,
    )
    assert upload.status_code == 200
    attachment_url = upload.json()["url"]

    assert client.get(attachment_url).status_code == 401
    owner_token = owner_headers["Authorization"].split(" ", 1)[1]
    owner_file = client.get(f"{attachment_url}?token={owner_token}")
    assert owner_file.status_code == 200
    assert owner_file.content == b"fake-image"

    forbidden = client.post(
        "/api/notes/upload-image",
        data={"note_id": note["id"]},
        files={"file": ("other.png", b"fake-image", "image/png")},
        headers=other_headers,
    )
    assert forbidden.status_code == 403

    deleted = client.delete(f"/api/notes/nodes/{note['id']}", headers=owner_headers)
    assert deleted.status_code == 200


def _receive_type(websocket, expected_type):
    for _ in range(8):
        message = websocket.receive_json()
        if message.get("type") == expected_type:
            return message
    raise AssertionError(f"Did not receive collaboration message: {expected_type}")


def test_collaboration_websocket_syncs_two_editors(client):
    owner_headers = _register_and_login(client, "collab-owner", "collab-owner@example.com")
    editor_headers = _register_and_login(client, "collab-editor", "collab-editor@example.com")
    notebook, note = _create_note(client, owner_headers)

    added = client.post(
        f"/api/notes/notebooks/{notebook['id']}/members",
        json={"username_or_email": "collab-editor", "role": "editor"},
        headers=owner_headers,
    )
    assert added.status_code == 200

    owner_ticket = client.post(
        f"/api/notes/{note['id']}/collaboration-ticket",
        headers=owner_headers,
    ).json()
    editor_ticket = client.post(
        f"/api/notes/{note['id']}/collaboration-ticket",
        headers=editor_headers,
    ).json()
    assert owner_ticket["can_edit"] is True
    assert editor_ticket["can_edit"] is True

    snapshot = base64.b64encode(b"initial-yjs-snapshot").decode("ascii")
    update = base64.b64encode(b"editor-yjs-update").decode("ascii")
    with client.websocket_connect(
        f"/api/notes/{note['id']}/collab?ticket={owner_ticket['ticket']}"
    ) as owner_socket:
        assert _receive_type(owner_socket, "init")["content"] == "initial"
        owner_socket.send_json({
            "type": "snapshot",
            "snapshot": snapshot,
            "content": "initial",
            "cursor": 0,
        })
        assert _receive_type(owner_socket, "snapshot-ack")["revision"] == 1

        with client.websocket_connect(
            f"/api/notes/{note['id']}/collab?ticket={editor_ticket['ticket']}"
        ) as editor_socket:
            sync = _receive_type(editor_socket, "sync")
            assert sync["snapshot"] == snapshot
            assert sync["content"] == "initial"

            editor_socket.send_json({
                "type": "update",
                "update": update,
                "content": "edited by editor",
            })
            owner_update = _receive_type(owner_socket, "update")
            editor_update = _receive_type(editor_socket, "update")
            assert owner_update["update"] == update
            assert editor_update["update"] == update
            assert _receive_type(editor_socket, "ack")["revision"] == 2

    assert client.get(f"/api/notes/{note['id']}", headers=owner_headers).json()["content"] == "edited by editor"
