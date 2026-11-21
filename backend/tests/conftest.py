"""Test setup: runs against the dedicated test database, applies the real Alembic
migrations once, and truncates data between tests (keeping seeded stages)."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class _TestUrl(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    test_database_url: str = (
        "postgresql+psycopg://dgs:dgs_local_dev@localhost:5433/dgs_workspace_test"
    )


TEST_URL = _TestUrl().test_database_url
if "test" not in TEST_URL.rsplit("/", 1)[-1]:
    raise RuntimeError(f"Refusing to run tests against a non-test database: {TEST_URL}")
os.environ["DATABASE_URL"] = TEST_URL  # must happen before the app is imported

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

DATA_TABLES = [
    "task_activity", "task_comments", "task_dependencies", "work_logs", "reports",
    "plan_notes", "tasks", "milestones", "workstreams", "projects",
    "knowledge_versions", "knowledge_project_links", "knowledge_task_links",
    "knowledge_relations", "knowledge_items", "methodology_versions", "project_deliverables",
    "project_methodologies", "deliverable_definitions", "methodology_activities",
    "methodology_stages", "methodologies", "document_task_links", "project_documents",
    "document_roots", "suggestions", "voice_notes",
]  # fmt: skip


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean():
    yield
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(DATA_TABLES)} CASCADE"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def project(client):
    r = client.post(
        "/api/projects",
        json={"name": "Test project", "workstreams": ["Backend", "Frontend"]},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def make_task(client, project):
    def _make(**fields):
        body = {"project_id": project["id"], "title": "A task", **fields}
        r = client.post("/api/tasks", json=body)
        assert r.status_code == 201, r.text
        return r.json()

    return _make
