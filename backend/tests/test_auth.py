from app.models.refresh_token import RefreshToken
from app.services.auth import decode_refresh_token


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


def test_login_persists_only_a_hashed_refresh_token_with_unique_jti(
    client, login_payload, db_session,
):
    response = client.post("/api/auth/login", data=login_payload)
    assert response.status_code == 200
    raw_refresh_token = response.json()["refresh_token"]

    record = db_session.query(RefreshToken).one()
    payload = decode_refresh_token(raw_refresh_token)
    assert payload is not None
    assert payload["jti"] == record.jti
    assert payload["sub"] == str(record.user_id)
    assert record.token_hash != raw_refresh_token
    assert len(record.token_hash) == 64


def test_refresh_token_is_single_use(client, login_payload):
    token = client.post("/api/auth/login", data=login_payload).json()["refresh_token"]

    first = client.post("/api/auth/refresh", json={"refresh_token": token})
    second = client.post("/api/auth/refresh", json={"refresh_token": token})

    assert first.status_code == 200
    assert second.status_code == 401


def test_replayed_refresh_token_revokes_its_replacement_chain(client, login_payload):
    token = client.post("/api/auth/login", data=login_payload).json()["refresh_token"]
    replacement = client.post(
        "/api/auth/refresh", json={"refresh_token": token}
    ).json()["refresh_token"]

    replay = client.post("/api/auth/refresh", json={"refresh_token": token})
    replacement_after_replay = client.post(
        "/api/auth/refresh", json={"refresh_token": replacement}
    )

    assert replay.status_code == 401
    assert replacement_after_replay.status_code == 401


def test_logout_revokes_submitted_refresh_token(client, login_payload):
    token = client.post("/api/auth/login", data=login_payload).json()["refresh_token"]

    logout = client.post("/api/auth/logout", json={"refresh_token": token})
    refresh = client.post("/api/auth/refresh", json={"refresh_token": token})

    assert logout.status_code == 200
    assert refresh.status_code == 401
