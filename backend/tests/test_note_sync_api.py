from uuid import UUID

import pytest


def _register_and_login(client, username, email):
    response = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "pass123456"},
    )
    assert response.status_code == 200
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "pass123456"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_notebook(client, headers):
    response = client.post(
        "/api/notes/notebooks",
        json={"name": "Sync notebook"},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def _sync_url(notebook_id, suffix="manifest"):
    return f"/api/notes/notebooks/{notebook_id}/sync/{suffix}"


def test_sync_manifest_is_owner_only_and_never_exposes_server_paths(client):
    owner = _register_and_login(client, "sync-owner", "sync-owner@example.com")
    other = _register_and_login(client, "sync-other", "sync-other@example.com")
    notebook = _create_notebook(client, owner)
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Plan", "content": "# Local plan"},
        headers=owner,
    ).json()

    response = client.get(_sync_url(notebook["id"]), headers=owner)
    assert response.status_code == 200
    payload = response.json()
    assert payload["notebook_id"] == notebook["id"]
    assert payload["revision"] >= 1
    assert any(item["node_id"] == note["id"] for item in payload["items"])
    assert all("content_path" not in item for item in payload["items"])
    assert all("notes_data" not in str(item) for item in payload["items"])

    forbidden = client.get(_sync_url(notebook["id"]), headers=other)
    assert forbidden.status_code == 403


def test_sync_changes_are_cursor_paginated_and_include_delete_tombstones(client):
    owner = _register_and_login(client, "sync-cursor", "sync-cursor@example.com")
    notebook = _create_notebook(client, owner)
    folder = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "Archive"},
        headers=owner,
    ).json()
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Old", "content": "old"},
        headers=owner,
    ).json()
    assert client.delete(f"/api/notes/nodes/{note['id']}", headers=owner).status_code == 200

    first = client.get(
        _sync_url(notebook["id"], "changes"),
        params={"after": 0, "limit": 1},
        headers=owner,
    )
    assert first.status_code == 200
    first_payload = first.json()
    assert first_payload["changes"]
    assert first_payload["has_more"] is True
    assert first_payload["changes"][0]["sequence"] > 0

    cursor = first_payload["cursor"]
    second = client.get(
        _sync_url(notebook["id"], "changes"),
        params={"after": cursor, "limit": 50},
        headers=owner,
    )
    assert second.status_code == 200
    tombstones = [change for change in second.json()["changes"] if change["operation"] == "delete"]
    assert tombstones
    assert tombstones[-1]["node_id"] == note["id"]
    assert tombstones[-1]["path"] == "/Old.md"
    assert second.json()["cursor"] >= cursor
    assert folder["id"] != note["id"]


def test_sync_content_batch_and_apply_update_are_idempotent(client):
    owner = _register_and_login(client, "sync-apply", "sync-apply@example.com")
    notebook = _create_notebook(client, owner)
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Plan", "content": "before"},
        headers=owner,
    ).json()

    content = client.post(
        _sync_url(notebook["id"], "content"),
        json={"node_ids": [note["id"]]},
        headers=owner,
    )
    assert content.status_code == 200
    assert content.json()["contents"] == {note["id"]: "before"}

    operation = {
        "client_operation_id": "device-1:1",
        "kind": "update_note",
        "node_id": note["id"],
        "path": "/Plan.md",
        "content": "after",
        "base_revision": note["content_revision"],
        "base_hash": "cba06b5736faf915f6f59c5b16d7c0e5f5e4d8e5a4d5b87d6c7d0a4c2f8e9f2e2",
    }
    # The server validates the supplied hash against the current content; use
    # the manifest hash for the actual apply request.
    manifest = client.get(_sync_url(notebook["id"]), headers=owner).json()
    operation["base_hash"] = next(item["content_hash"] for item in manifest["items"] if item["node_id"] == note["id"])

    applied = client.post(
        _sync_url(notebook["id"], "apply"),
        json={"operations": [operation]},
        headers=owner,
    )
    assert applied.status_code == 200
    result = applied.json()["results"][0]
    assert result["status"] == "applied"
    assert result["node"]["content_revision"] == note["content_revision"] + 1

    replay = client.post(
        _sync_url(notebook["id"], "apply"),
        json={"operations": [operation]},
        headers=owner,
    )
    assert replay.status_code == 200
    assert replay.json()["results"][0]["status"] == "already_applied"
    assert client.get(f"/api/notes/{note['id']}", headers=owner).json()["content"] == "after"


def test_sync_apply_reports_stale_revision_as_recoverable_conflict(client):
    owner = _register_and_login(client, "sync-conflict", "sync-conflict@example.com")
    notebook = _create_notebook(client, owner)
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Conflict", "content": "base"},
        headers=owner,
    ).json()
    current = client.put(
        f"/api/notes/{note['id']}",
        json={"content": "remote", "base_revision": note["content_revision"]},
        headers=owner,
    ).json()
    manifest = client.get(_sync_url(notebook["id"]), headers=owner).json()
    base_hash = next(item["content_hash"] for item in manifest["items"] if item["node_id"] == note["id"])

    response = client.post(
        _sync_url(notebook["id"], "apply"),
        json={
            "operations": [{
                "client_operation_id": "device-conflict:1",
                "kind": "update_note",
                "node_id": note["id"],
                "path": "/Conflict.md",
                "content": "local",
                "base_revision": note["content_revision"],
                "base_hash": base_hash,
            }]
        },
        headers=owner,
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "conflict"
    assert result["error_code"] == "STALE_REVISION"
    assert result["node"]["content_revision"] == current["content_revision"]

    conflicts = client.get(_sync_url(notebook["id"], "conflicts"), headers=owner)
    assert conflicts.status_code == 200
    assert conflicts.json()["conflicts"][0]["status"] == "open"


def test_sync_apply_records_remote_deletion_and_keep_local_recreates_note(client):
    owner = _register_and_login(client, "sync-delete-conflict", "sync-delete-conflict@example.com")
    notebook = _create_notebook(client, owner)
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"title": "Recover", "content": "base"},
        headers=owner,
    ).json()
    manifest = client.get(_sync_url(notebook["id"]), headers=owner).json()
    base_hash = next(item["content_hash"] for item in manifest["items"] if item["node_id"] == note["id"])
    assert client.delete(f"/api/notes/nodes/{note['id']}", headers=owner).status_code == 200

    response = client.post(
        _sync_url(notebook["id"], "apply"),
        json={
            "operations": [{
                "client_operation_id": "device-delete-conflict:1",
                "kind": "update_note",
                "node_id": note["id"],
                "path": "/Recover.md",
                "local_path": "Recover.md",
                "content": "local",
                "base_revision": note["content_revision"],
                "base_hash": base_hash,
            }]
        },
        headers=owner,
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "conflict"
    assert result["error_code"] == "REMOTE_DELETED"
    conflict_id = result["conflict_id"]

    conflicts = client.get(_sync_url(notebook["id"], "conflicts"), headers=owner).json()["conflicts"]
    conflict = next(item for item in conflicts if item["id"] == conflict_id)
    assert conflict["status"] == "open"
    assert conflict["node_id"] == note["id"]
    assert conflict["local_path"] == "Recover.md"

    resolved = client.post(
        f"{_sync_url(notebook['id'], 'conflicts')}/{conflict_id}/resolve",
        json={"resolution": "keep_local", "content": "local"},
        headers=owner,
    )
    assert resolved.status_code == 200
    recreated = resolved.json()["results"][0]["node"]
    assert recreated["path"] == "/Recover.md"
    assert recreated["node_id"] != note["id"]
    assert client.get(f"/api/notes/{recreated['node_id']}", headers=owner).json()["content"] == "local"


def test_sync_apply_creates_moves_and_deletes_nodes_with_stable_ids(client):
    owner = _register_and_login(client, "sync-tree", "sync-tree@example.com")
    notebook = _create_notebook(client, owner)
    root = notebook["id"]

    folder_result = client.post(
        _sync_url(root, "apply"),
        json={"operations": [{
            "client_operation_id": "tree:folder",
            "kind": "create_folder",
            "name": "Projects",
            "path": "/Projects",
            "local_path": "Projects",
        }]},
        headers=owner,
    ).json()["results"][0]
    assert folder_result["status"] == "applied"
    folder_id = folder_result["node"]["node_id"]

    note_result = client.post(
        _sync_url(root, "apply"),
        json={"operations": [{
            "client_operation_id": "tree:note",
            "kind": "create_note",
            "parent_id": folder_id,
            "name": "Plan.md",
            "path": "/Projects/Plan.md",
            "local_path": "Projects/Plan.md",
            "content": "# Plan",
        }]},
        headers=owner,
    ).json()["results"][0]
    assert note_result["status"] == "applied"
    note_id = note_result["node"]["node_id"]

    moved = client.post(
        _sync_url(root, "apply"),
        json={"operations": [{
            "client_operation_id": "tree:move",
            "kind": "move_node",
            "node_id": note_id,
            "parent_id": None,
            "path": "/Plan.md",
            "local_path": "Plan.md",
        }]},
        headers=owner,
    ).json()["results"][0]
    assert moved["status"] == "applied"
    assert moved["node"]["node_id"] == note_id
    assert moved["node"]["path"] == "/Plan.md"

    deleted = client.post(
        _sync_url(root, "apply"),
        json={"operations": [{
            "client_operation_id": "tree:delete",
            "kind": "delete_node",
            "node_id": note_id,
            "path": "/Plan.md",
            "local_path": "Plan.md",
        }]},
        headers=owner,
    ).json()["results"][0]
    assert deleted["status"] == "applied"
    manifest = client.get(_sync_url(root), headers=owner).json()
    assert all(item["node_id"] != note_id for item in manifest["items"])


def test_sync_apply_rejects_path_escape_before_mutating_tree(client):
    owner = _register_and_login(client, "sync-path", "sync-path@example.com")
    notebook = _create_notebook(client, owner)
    response = client.post(
        _sync_url(notebook["id"], "apply"),
        json={"operations": [{
            "client_operation_id": "path:1",
            "kind": "create_note",
            "name": "bad.md",
            "path": "/../bad.md",
            "content": "unsafe",
        }]},
        headers=owner,
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "rejected"
    assert result["error_code"] == "INVALID_SYNC_PATH"
    assert client.get(_sync_url(notebook["id"]), headers=owner).json()["items"] == []


@pytest.mark.parametrize("suffix", ["manifest", "changes", "content", "apply", "conflicts"])
def test_sync_routes_reject_unknown_notebook(client, suffix):
    owner = _register_and_login(client, "sync-missing", "sync-missing@example.com")
    missing = "00000000-0000-0000-0000-000000000099"
    method = client.post if suffix in {"content", "apply"} else client.get
    kwargs = {"headers": owner}
    if suffix == "content":
        kwargs["json"] = {"node_ids": []}
    elif suffix == "apply":
        kwargs["json"] = {"operations": []}
    response = method(_sync_url(missing, suffix), **kwargs)
    assert response.status_code in {403, 404}
