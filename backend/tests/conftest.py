import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


os.environ.setdefault("DATABASE_URL", "sqlite:///./test_bootstrap.db")
os.environ.setdefault("QDRANT_URL", "http://qdrant:6333")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")


from app.core.config import settings
from app.database.database import Base, get_db
from app.main import app
import app.main as main_module

from app.models.user import User
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.parsing_job import ParsingJob


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


class FakeDbConnection:
    def execute(self, statement):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeHealthEngine:
    def connect(self):
        return FakeDbConnection()


@pytest.fixture(autouse=True)
def test_environment(monkeypatch, tmp_path):
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    settings.rate_limit_enabled = False
    settings.upload_dir = str(tmp_path / "uploads")

    monkeypatch.setattr(
        main_module,
        "engine",
        FakeHealthEngine(),
    )

    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def registered_user_payload():
    return {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "StrongPassword123",
    }


def register_test_user(client, user_payload=None):
    payload = user_payload or {
        "full_name": "Test User",
        "email": "test@example.com",
        "password": "StrongPassword123",
    }

    return client.post(
        "/auth/register",
        json=payload,
    )


def login_test_user(
    client,
    email="test@example.com",
    password="StrongPassword123",
):
    return client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )


@pytest.fixture()
def auth_headers(client, registered_user_payload):
    register_response = register_test_user(
        client=client,
        user_payload=registered_user_payload,
    )

    assert register_response.status_code == 201

    login_response = login_test_user(
        client=client,
        email=registered_user_payload["email"],
        password=registered_user_payload["password"],
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}",
    }