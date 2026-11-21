"""Document indexing must be read-only and must never escape a registered folder."""

import os
import shutil
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "_tmp_docs"  # inside the repo (under $HOME), git-ignored


@pytest.fixture
def folder():
    shutil.rmtree(FIXTURE, ignore_errors=True)
    (FIXTURE / "docs" / "adr").mkdir(parents=True)
    (FIXTURE / "node_modules" / "pkg").mkdir(parents=True)
    (FIXTURE / "docs" / "adr" / "0001-use-postgres.md").write_text("# ADR 1\nUse Postgres.")
    (FIXTURE / "docs" / "architecture.md").write_text("# Architecture\nA monolith.")
    (FIXTURE / "README.md").write_text("Hello")
    (FIXTURE / "diagram.png").write_bytes(b"\x89PNG")
    (FIXTURE / ".env").write_text("SECRET=1")
    (FIXTURE / "server.pem").write_text("-----BEGIN-----")
    (FIXTURE / "aws_credentials.txt").write_text("key")
    (FIXTURE / "node_modules" / "pkg" / "readme.md").write_text("dependency")
    outside = FIXTURE.parent / "_tmp_outside.md"
    outside.write_text("outside the root")
    os.symlink(outside, FIXTURE / "escape.md")
    yield FIXTURE
    shutil.rmtree(FIXTURE, ignore_errors=True)
    outside.unlink(missing_ok=True)


def register(client, path, **extra):
    return client.post("/api/document-roots", json={"name": "Docs", "path": str(path), **extra})


def test_root_validation(client, folder):
    cases = [
        ("relative/path", "absolute"),
        ("/does/not/exist", "does not exist"),
        ("/", "cannot be registered"),
        (str(Path.home()), "cannot be registered"),
        ("/etc", "cannot be registered"),
        (str(folder / "README.md"), "is a file"),
    ]
    for bad, msg in cases:
        r = register(client, bad)
        assert r.status_code == 400, bad
        assert msg in r.json()["error"]["message"], bad
    r = register(client, folder)
    assert r.status_code == 201 and r.json()["path"] == str(folder.resolve())
    assert register(client, folder).status_code == 409


def test_scan_excludes_secrets_dependencies_hidden_and_symlinks(client, folder):
    root = register(client, folder).json()
    scan = client.post(f"/api/document-roots/{root['id']}/scan").json()
    paths = {f["relative_path"]: f["suggested_category"] for f in scan["files"]}
    assert paths == {
        "README.md": "other",
        "diagram.png": "diagram",
        "docs/architecture.md": "architecture",
        "docs/adr/0001-use-postgres.md": "adr",
    }


def test_register_preview_and_traversal_protection(client, folder, project):
    root = register(client, folder, project_id=project["id"]).json()
    r = client.post(
        f"/api/document-roots/{root['id']}/register",
        json={"paths": ["docs/architecture.md", "docs/architecture.md"]},
    )
    assert r.status_code == 201 and len(r.json()) == 1
    doc = r.json()[0]
    assert doc["category"] == "architecture" and doc["project_name"] == "Test project"
    assert doc["source"] == "file" and doc["file_available"] is True
    assert (
        client.get(f"/api/documents/{doc['id']}/preview")
        .json()["text"]
        .startswith("# Architecture")
    )
    for evil in [
        "../_tmp_outside.md",
        "escape.md",
        ".env",
        "server.pem",
        "/etc/passwd",
        "node_modules/pkg/readme.md",
        "docs/../../_tmp_outside.md",
    ]:
        r = client.post(f"/api/document-roots/{root['id']}/register", json={"paths": [evil]})
        assert r.status_code == 400, evil
        assert r.json()["error"]["code"] == "invalid_path", evil
    # Binary files are indexed but not previewed
    img = client.post(
        f"/api/document-roots/{root['id']}/register", json={"paths": ["diagram.png"]}
    ).json()[0]
    assert client.get(f"/api/documents/{img['id']}/preview").status_code == 400


def test_files_are_never_modified_or_deleted(client, folder):
    root = register(client, folder).json()
    doc = client.post(
        f"/api/document-roots/{root['id']}/register", json={"paths": ["README.md"]}
    ).json()[0]
    assert (
        client.patch(f"/api/documents/{doc['id']}", json={"content": "overwrite!"}).status_code
        == 400
    )
    assert client.delete(f"/api/documents/{doc['id']}").status_code == 204
    assert (folder / "README.md").read_text() == "Hello"
    doc = client.post(
        f"/api/document-roots/{root['id']}/register", json={"paths": ["README.md"]}
    ).json()[0]
    assert client.delete(f"/api/document-roots/{root['id']}").status_code == 400  # needs confirm
    assert client.delete(f"/api/document-roots/{root['id']}?confirm=true").status_code == 204
    assert (folder / "README.md").exists()
    assert client.get(f"/api/documents/{doc['id']}").status_code == 404


def test_missing_file_is_flagged(client, folder):
    root = register(client, folder).json()
    doc = client.post(
        f"/api/document-roots/{root['id']}/register", json={"paths": ["README.md"]}
    ).json()[0]
    (folder / "README.md").unlink()
    assert client.get(f"/api/documents/{doc['id']}").json()["file_available"] is False


def test_links_notes_tasks_and_search(client, project, make_task):
    assert (
        client.post("/api/documents", json={"title": "x", "url": "javascript:alert(1)"}).status_code
        == 422
    )
    link = client.post(
        "/api/documents",
        json={
            "title": "Figma designs",
            "url": "https://figma.com/x",
            "category": "design",
            "project_id": project["id"],
        },
    ).json()
    assert link["source"] == "link"
    note = client.post(
        "/api/documents",
        json={"title": "Release notes v1", "content": "Shipped login", "category": "release_notes"},
    ).json()
    assert note["source"] == "note"
    t = make_task()
    r = client.post(f"/api/documents/{link['id']}/tasks", json={"task_id": t["id"]})
    assert r.json()["tasks"][0]["task_title"] == "A task"
    assert (
        client.post(f"/api/documents/{link['id']}/tasks", json={"task_id": t["id"]}).status_code
        == 409
    )
    assert [d["title"] for d in client.get("/api/documents?category=design").json()] == [
        "Figma designs"
    ]
    assert any(h["type"] == "document" for h in client.get("/api/search?q=shipped").json())
