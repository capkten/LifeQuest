def _register_and_login(client, username="testuser", email="test@example.com"):
    """Helper: register a user and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_update_username_duplicate_returns_400(client):
    """Updating to an existing username should return 400, not 500."""
    headers1 = _register_and_login(client, "user1", "user1@example.com")
    _register_and_login(client, "user2", "user2@example.com")

    response = client.put(
        "/api/users/me",
        json={"username": "user2", "email": "user1@example.com"},
        headers=headers1,
    )
    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]


def test_update_email_duplicate_returns_400(client):
    """Updating to an existing email should return 400, not 500."""
    headers1 = _register_and_login(client, "user1", "user1@example.com")
    _register_and_login(client, "user2", "user2@example.com")

    response = client.put(
        "/api/users/me",
        json={"username": "user1", "email": "user2@example.com"},
        headers=headers1,
    )
    assert response.status_code == 400
    assert "Email already exists" in response.json()["detail"]


def test_update_same_username_no_conflict(client):
    """Updating with the same current username should not trigger a conflict."""
    headers = _register_and_login(client)

    response = client.put(
        "/api/users/me",
        json={"username": "testuser", "email": "test@example.com"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"


def test_update_avatar_only(client):
    """Updating only the avatar should succeed."""
    headers = _register_and_login(client)

    response = client.put(
        "/api/users/me",
        json={"avatar": "/uploads/avatars/new.png"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["avatar"] == "/uploads/avatars/new.png"
