def test_register(client):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_register_duplicate_username(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test1@example.com",
            "password": "testpassword123"
        }
    )
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test2@example.com",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 400


def test_login(client):
    # Register first
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    # Login
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    # Register first
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    # Login with wrong password
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401


def test_username_change_preserves_session(client):
    """Changing username should not invalidate the current token."""
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify current user
    me_response = client.get("/api/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testuser"

    # Update username
    update_response = client.put(
        "/api/users/me",
        json={"username": "newname", "email": "test@example.com"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["username"] == "newname"

    # Old token should still work
    me_response2 = client.get("/api/users/me", headers=headers)
    assert me_response2.status_code == 200
    assert me_response2.json()["username"] == "newname"


def test_old_username_token_returns_401(client):
    """A token with sub=username (old format) should return 401, not 500."""
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    # Simulate an old-format token with sub=username
    from app.services.auth import create_access_token
    from datetime import timedelta
    old_token = create_access_token(
        data={"sub": "testuser"}, expires_delta=timedelta(minutes=30)
    )
    headers = {"Authorization": f"Bearer {old_token}"}

    response = client.get("/api/users/me", headers=headers)
    assert response.status_code == 401
