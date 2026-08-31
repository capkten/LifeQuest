import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")


def _register_and_login(client, username="linkuser", email="link@example.com", password="pass123456"):
    response = client.post(
        "/api/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_notebook(client, headers, name="Execution notebook"):
    response = client.post("/api/notes/notebooks", json={"name": name}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _create_targets(client, headers, notebook_id):
    note = client.post(
        f"/api/notes/notebooks/{notebook_id}/notes",
        json={"title": "Weekly plan", "content": "# Plan"},
        headers=headers,
    )
    task = client.post(
        "/api/todos/tasks",
        json={"title": "Ship the plan"},
        headers=headers,
    )
    goal = client.post(
        "/api/todos/goals",
        json={"title": "Finish the quarter"},
        headers=headers,
    )
    project = client.post(
        "/api/projects",
        json={"name": "Plan project"},
        headers=headers,
    )
    for response in (note, task, goal, project):
        assert response.status_code == 200, response.text
    return note.json(), task.json(), goal.json(), project.json()


def test_links_return_target_summaries_and_can_be_read_from_each_side(client):
    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers)
    note, task, goal, project = _create_targets(client, headers, notebook["id"])

    for kind, target_id in (
        ("task", task["id"]),
        ("goal", goal["id"]),
        ("project", project["id"]),
    ):
        response = client.post(
            f"/api/notes/{note['id']}/links",
            json={"kind": kind, "target_id": target_id},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        summary = response.json()
        assert summary["kind"] == kind
        assert summary["id"] == target_id
        assert summary["title"]
        assert summary["url"]

    links = client.get(f"/api/notes/{note['id']}/links", headers=headers)
    assert links.status_code == 200, links.text
    assert {(item["kind"], item["id"]) for item in links.json()} == {
        ("task", task["id"]),
        ("goal", goal["id"]),
        ("project", project["id"]),
    }

    task_notes = client.get(f"/api/todos/tasks/{task['id']}/notes", headers=headers)
    goal_notes = client.get(f"/api/todos/goals/{goal['id']}/notes", headers=headers)
    project_notes = client.get(f"/api/projects/{project['id']}/notes", headers=headers)
    assert task_notes.status_code == 200
    assert goal_notes.status_code == 200
    assert project_notes.status_code == 200
    assert task_notes.json()[0] == {
        "kind": "note",
        "id": note["id"],
        "title": note["name"],
        "url": f"/notes/{notebook['id']}/view/{note['id']}",
    }
    assert goal_notes.json()[0]["id"] == note["id"]
    assert project_notes.json()[0]["id"] == note["id"]


def test_duplicate_link_is_rejected_without_creating_a_second_row(client):
    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers)
    note, task, _, _ = _create_targets(client, headers, notebook["id"])
    payload = {"kind": "task", "target_id": task["id"]}

    first = client.post(f"/api/notes/{note['id']}/links", json=payload, headers=headers)
    second = client.post(f"/api/notes/{note['id']}/links", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "LINK_ALREADY_EXISTS"
    assert len(client.get(f"/api/notes/{note['id']}/links", headers=headers).json()) == 1


def test_link_creation_rejects_cross_user_note_or_target(client):
    owner_headers = _register_and_login(client)
    notebook = _create_notebook(client, owner_headers)
    note, task, _, _ = _create_targets(client, owner_headers, notebook["id"])

    other_headers = _register_and_login(
        client,
        username="otherlinkuser",
        email="other-link@example.com",
    )
    other_task = client.post(
        "/api/todos/tasks",
        json={"title": "Other task"},
        headers=other_headers,
    ).json()

    assert client.post(
        f"/api/notes/{note['id']}/links",
        json={"kind": "task", "target_id": task["id"]},
        headers=other_headers,
    ).status_code == 403
    assert client.post(
        f"/api/notes/{note['id']}/links",
        json={"kind": "task", "target_id": other_task["id"]},
        headers=owner_headers,
    ).status_code == 403


def test_viewer_cannot_change_links_but_can_read_them(client):
    owner_headers = _register_and_login(client)
    notebook = _create_notebook(client, owner_headers)
    note, task, _, _ = _create_targets(client, owner_headers, notebook["id"])
    assert client.post(
        f"/api/notes/{note['id']}/links",
        json={"kind": "task", "target_id": task["id"]},
        headers=owner_headers,
    ).status_code == 200

    viewer_headers = _register_and_login(
        client,
        username="linkviewer",
        email="link-viewer@example.com",
    )
    member = client.post(
        f"/api/notes/notebooks/{notebook['id']}/members",
        json={"username_or_email": "linkviewer", "role": "viewer"},
        headers=owner_headers,
    )
    assert member.status_code == 200, member.text

    assert client.get(f"/api/notes/{note['id']}/links", headers=viewer_headers).status_code == 200
    denied = client.delete(
        f"/api/notes/{note['id']}/links/task/{task['id']}",
        headers=viewer_headers,
    )
    assert denied.status_code == 403


def test_unlink_is_explicit_and_does_not_delete_the_note_or_target(client):
    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers)
    note, task, _, _ = _create_targets(client, headers, notebook["id"])
    assert client.post(
        f"/api/notes/{note['id']}/links",
        json={"kind": "task", "target_id": task["id"]},
        headers=headers,
    ).status_code == 200

    response = client.delete(
        f"/api/notes/{note['id']}/links/task/{task['id']}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"message": "Link removed"}
    assert client.get(f"/api/notes/{note['id']}/links", headers=headers).json() == []
    assert client.get(f"/api/notes/{note['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/todos/tasks/{task['id']}", headers=headers).status_code == 200


def test_deleting_a_note_cleans_all_link_rows(client, db_session):
    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers)
    note, task, goal, project = _create_targets(client, headers, notebook["id"])
    for kind, target_id in (
        ("task", task["id"]),
        ("goal", goal["id"]),
        ("project", project["id"]),
    ):
        assert client.post(
            f"/api/notes/{note['id']}/links",
            json={"kind": kind, "target_id": target_id},
            headers=headers,
        ).status_code == 200

    assert client.delete(f"/api/notes/nodes/{note['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/todos/tasks/{task['id']}/notes", headers=headers).json() == []
    assert client.get(f"/api/todos/goals/{goal['id']}/notes", headers=headers).json() == []
    assert client.get(f"/api/projects/{project['id']}/notes", headers=headers).json() == []

    from app.models.note_link import GoalNoteLink, ProjectNoteLink, TaskNoteLink

    assert db_session.query(TaskNoteLink).count() == 0
    assert db_session.query(GoalNoteLink).count() == 0
    assert db_session.query(ProjectNoteLink).count() == 0


@pytest.mark.parametrize("kind", ["unknown", "habit"])
def test_link_kind_is_explicitly_validated(client, kind):
    headers = _register_and_login(client)
    notebook = _create_notebook(client, headers)
    note, _, _, _ = _create_targets(client, headers, notebook["id"])

    response = client.post(
        f"/api/notes/{note['id']}/links",
        json={"kind": kind, "target_id": note["id"]},
        headers=headers,
    )
    assert response.status_code == 422
