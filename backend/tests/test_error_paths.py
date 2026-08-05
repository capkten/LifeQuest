def test_health_and_invalid_input_paths_return_explicit_errors(client):
    assert client.get("/api/health").status_code == 200
    response = client.post(
        "/api/auth/login",
        data={"username": "missing", "password": "missing"},
    )
    assert response.status_code in {400, 401}
