def test_create_notebook(client):
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
        data={"username": "testuser", "password": "testpassword123"}
    )
    token = login_response.json()["access_token"]

    # Create notebook
    response = client.post(
        "/api/notes/notebooks",
        json={"name": "My Notebook", "description": "Test notebook"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My Notebook"


def test_create_note(client):
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
        data={"username": "testuser", "password": "testpassword123"}
    )
    token = login_response.json()["access_token"]

    # Create notebook
    notebook_response = client.post(
        "/api/notes/notebooks",
        json={"name": "My Notebook"},
        headers={"Authorization": f"Bearer {token}"}
    )
    notebook_id = notebook_response.json()["id"]

    # Create folder
    folder_response = client.post(
        "/api/notes/folders",
        json={"name": "My Folder", "notebook_id": notebook_id},
        headers={"Authorization": f"Bearer {token}"}
    )
    folder_id = folder_response.json()["id"]

    # Create note
    response = client.post(
        "/api/notes/",
        json={
            "title": "Test Note",
            "folder_id": folder_id,
            "content": "# Test\nThis is a test note."
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Note"
