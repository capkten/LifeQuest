from uuid import UUID

from app.models.note_sync import NoteSyncChange, NoteSyncOperation


def _login(client, username="sync-ledger", email="sync-ledger@example.com"):
    client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": "pass123456"},
    )
    token = client.post(
        "/api/auth/login",
        data={"username": username, "password": "pass123456"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_note_mutations_allocate_monotonic_sync_sequences_and_hashes(client, db_session):
    headers = _login(client)
    notebook = client.post(
        "/api/notes/notebooks",
        json={"name": "Ledger"},
        headers=headers,
    ).json()
    folder = client.post(
        f"/api/notes/notebooks/{notebook['id']}/folders",
        json={"name": "Journal"},
        headers=headers,
    ).json()
    note = client.post(
        f"/api/notes/notebooks/{notebook['id']}/notes",
        json={"parent_id": folder["id"], "title": "Today", "content": "first"},
        headers=headers,
    ).json()
    updated = client.put(
        f"/api/notes/{note['id']}",
        json={"content": "second", "base_revision": note["content_revision"]},
        headers=headers,
    ).json()
    assert updated["content_revision"] == note["content_revision"] + 1
    assert client.patch(
        f"/api/notes/nodes/{note['id']}",
        json={"name": "Tomorrow"},
        headers=headers,
    ).status_code == 200

    rows = (
        db_session.query(NoteSyncChange)
        .filter(NoteSyncChange.notebook_id == UUID(notebook["id"]))
        .order_by(NoteSyncChange.sequence.asc())
        .all()
    )
    assert [row.sequence for row in rows] == list(range(1, len(rows) + 1))
    assert [row.operation for row in rows[:3]] == ["create", "create", "update"]
    assert rows[1].content_hash is not None
    assert rows[2].content_hash != rows[1].content_hash
    assert rows[-1].path == "/Journal/Tomorrow.md"

    assert client.delete(f"/api/notes/nodes/{note['id']}", headers=headers).status_code == 200
    tombstone = (
        db_session.query(NoteSyncChange)
        .filter(
            NoteSyncChange.notebook_id == UUID(notebook["id"]),
            NoteSyncChange.operation == "delete",
            NoteSyncChange.node_id == UUID(note["id"]),
        )
        .one()
    )
    assert tombstone.path == "/Journal/Tomorrow.md"
    assert tombstone.content_hash == rows[-1].content_hash


def test_sync_operation_ledger_has_unique_notebook_client_id(client, db_session):
    headers = _login(client, "sync-ledger-unique", "sync-ledger-unique@example.com")
    notebook = client.post(
        "/api/notes/notebooks",
        json={"name": "Ledger unique"},
        headers=headers,
    ).json()
    first = NoteSyncOperation(
        notebook_id=UUID(notebook["id"]),
        client_operation_id="device:1",
        operation="update_note",
        result_json='{"status":"applied"}',
    )
    db_session.add(first)
    db_session.commit()
    duplicate = NoteSyncOperation(
        notebook_id=UUID(notebook["id"]),
        client_operation_id="device:1",
        operation="update_note",
        result_json='{"status":"applied"}',
    )
    db_session.add(duplicate)
    try:
        with __import__("pytest").raises(Exception):
            db_session.commit()
    finally:
        db_session.rollback()
