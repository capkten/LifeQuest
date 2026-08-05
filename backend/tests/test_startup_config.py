import pytest

from app import main


def test_health_endpoint_requires_no_authentication(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_reports_database_failure(client, monkeypatch):
    def fail_connect():
        raise OSError("database unavailable")

    monkeypatch.setattr(main.engine, "connect", fail_connect)
    response = client.get("/api/health")
    assert response.status_code == 503
