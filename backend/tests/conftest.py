import os
import tempfile
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
_runtime_directory = tempfile.TemporaryDirectory(prefix="lifequest-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_runtime_directory.name) / 'startup.db'}"
os.environ["MCP_AUTOSTART"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.achievement import AchievementService

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def isolated_files(tmp_path):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.services.note.NOTES_DIR", tmp_path / "notes_data")
        patch.setattr("app.api.notes.UPLOAD_DIR", tmp_path / "uploads" / "notes")
        avatar_dir = tmp_path / "uploads" / "avatars"
        avatar_dir.mkdir(parents=True)
        patch.setattr("app.api.users.UPLOAD_DIR", avatar_dir)
        yield


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    # Seed achievements in the test database
    db = TestingSessionLocal()
    try:
        service = AchievementService(db)
        service.seed_achievements()
    finally:
        db.close()
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
