"""Browser extension endpoints: keep AI answers, preview and confirmed file writes (ADR 0011)."""

import os
import shutil
from pathlib import Path

import pytest

FOLDER = Path(__file__).parent / "_tmp_clips"
OUTSIDE = Path(__file__).parent / "_tmp_clips_outside"


@pytest.fixture
def token(client):
    return client.get("/api/claude/setup").json()["token"]


@pytest.fixture
def h(token):
    return {"X-Workspace-Token": token}


@pytest.fixture
def folder(client, project):
    shutil.rmtree(FOLDER, ignore_errors=True)
    shutil.rmtree(OUTSIDE, ignore_errors=True)
    (FOLDER / "src").mkdir(parents=True)
    (FOLDER / "src" / "app.py").write_text("print('old')\n")
    OUTSIDE.mkdir()
    r = client.put(f"/api/projects/{project['id']}/connection", json={"path": str(FOLDER)})
    assert r.status_code == 200, r.text
    yield FOLDER
    shutil.rmtree(FOLDER, ignore_errors=True)
    shutil.rmtree(OUTSIDE, ignore_errors=True)


def allow_writes(client, on=True):
    assert client.put("/api/claude/settings", json={"allow_file_writes": on}).status_code == 200


def test_token_is_required(client, project):
    assert client.get("/api/clips/projects").status_code == 401
    r = client.post("/api/clips", json={"project_id": project["id"], "items": [{"text": "x"}]})
    assert r.status_code == 401
    r = client.post(
        "/api/clips",
        headers={"X-Workspace-Token": "wrong"},
        json={"project_id": project["id"], "items": [{"text": "x"}]},
    )
    assert r.status_code == 401


def test_projects_for_the_picker(client, project, h):
    d = client.get("/api/clips/projects", headers=h).json()
    assert [p["name"] for p in d["projects"]] == ["Test project"]
    assert d["projects"][0]["has_folder"] is False and d["file_writes_allowed"] is False


def test_keep_answers_as_a_note(client, project, h):
    client.put("/api/privacy/names", json=[{"name": "Jane Doe", "replacement": "the reviewer"}])
    body = {
        "project_id": project["id"],
        "items": [
            {"text": "## Architecture\nUse FastAPI. Ask Jane Doe to review.", "tool": "chatgpt",
             "url": "https://chatgpt.com/c/abc"},
            {"text": "print('hi')", "kind": "code", "language": "python", "tool": "chatgpt"},
        ],
    }  # fmt: skip
    r = client.post("/api/clips", headers=h, json=body)
    assert r.status_code == 201, r.text
    assert r.json()["saved_as"] == "note"
    docs = client.get("/api/documents", params={"project_id": project["id"]}).json()
    doc = client.get(f"/api/documents/{docs[0]['id']}").json()
    assert doc["title"] == "Architecture"
    assert "ai-clip" in doc["tags"] and "chatgpt" in doc["tags"]
    assert doc["url"] == "https://chatgpt.com/c/abc"
    assert "```python\nprint('hi')\n```" in doc["content"]
    assert "Jane Doe" not in doc["content"] and "the reviewer" in doc["content"]
    assert "Kept from ChatGPT" in doc["description"]


def test_keep_as_update_into_a_new_project(client, h):
    r = client.post(
        "/api/clips",
        headers=h,
        json={"new_project_name": "Idea from Gemini", "save_as": "update",
              "items": [{"text": "Master prompt: build a tracker", "tool": "gemini"}]},
    )  # fmt: skip
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["created_project"] and out["saved_as"] == "update"
    logs = client.get("/api/work-logs", params={"project_id": out["project_id"]}).json()
    assert len(logs) == 1 and "Master prompt" in logs[0]["summary"]
    assert "Kept from Gemini" in logs[0]["summary"]


def test_keep_needs_a_project(client, h):
    assert client.post("/api/clips", headers=h, json={"items": [{"text": "x"}]}).status_code == 422


def test_preview_then_write(client, project, h, folder):
    pid = project["id"]
    p = client.post(
        f"/api/projects/{pid}/files/preview", headers=h,
        json={"path": "src/app.py", "content": "print('new')\n"},
    ).json()  # fmt: skip
    assert p["exists"] and not p["will_create"] and p["writes_allowed"] is False
    assert "-print('old')" in p["diff"] and "+print('new')" in p["diff"]
    body = {
        "path": "src/app.py",
        "content": "print('new')\n",
        "expected_sha256": p["current_sha256"],
    }
    r = client.post(f"/api/projects/{pid}/files/write", headers=h, json=body)
    assert r.status_code == 403 and r.json()["error"]["code"] == "writes_disabled"
    assert (folder / "src" / "app.py").read_text() == "print('old')\n"

    allow_writes(client)
    r = client.post(f"/api/projects/{pid}/files/write", headers=h, json=body)
    assert r.status_code == 200, r.text
    assert r.json() == {"path": "src/app.py", "created": False, "bytes": 13}
    assert (folder / "src" / "app.py").read_text() == "print('new')\n"
    # A new file in a new folder.
    p2 = client.post(
        f"/api/projects/{pid}/files/preview", headers=h,
        json={"path": "docs/notes/plan.md", "content": "# Plan\n"},
    ).json()  # fmt: skip
    assert p2["will_create"] and p2["current_sha256"] is None
    r = client.post(
        f"/api/projects/{pid}/files/write", headers=h,
        json={"path": "docs/notes/plan.md", "content": "# Plan\n", "expected_sha256": None},
    )  # fmt: skip
    assert r.status_code == 200 and r.json()["created"]
    assert (folder / "docs" / "notes" / "plan.md").read_text() == "# Plan\n"
    assert oct((folder / "docs" / "notes" / "plan.md").stat().st_mode & 0o777) == "0o644"
    assert not list(folder.rglob(".dgs-*.tmp"))  # no temporary files left
    events = client.get(f"/api/projects/{pid}/code-events", params={"kind": "file_written"}).json()
    assert len(events) == 2


def test_write_refuses_if_the_file_changed_since_preview(client, project, h, folder):
    allow_writes(client)
    pid = project["id"]
    p = client.post(
        f"/api/projects/{pid}/files/preview",
        headers=h,
        json={"path": "src/app.py", "content": "x\n"},
    ).json()
    (folder / "src" / "app.py").write_text("someone else edited this\n")
    r = client.post(
        f"/api/projects/{pid}/files/write", headers=h,
        json={"path": "src/app.py", "content": "x\n", "expected_sha256": p["current_sha256"]},
    )  # fmt: skip
    assert r.status_code == 409
    assert (folder / "src" / "app.py").read_text() == "someone else edited this\n"
    # A "new" file that appeared meanwhile is not overwritten either.
    (folder / "late.txt").write_text("exists now")
    r = client.post(
        f"/api/projects/{pid}/files/write", headers=h,
        json={"path": "late.txt", "content": "y", "expected_sha256": None},
    )  # fmt: skip
    assert r.status_code == 409 and (folder / "late.txt").read_text() == "exists now"


@pytest.mark.parametrize(
    "path",
    ["../escape.py", "/etc/passwd", "~/x.py", "src/../../x.py", ".env", "config/.env.local",
     "keys/server.pem", ".git/config", "node_modules/pkg/index.js", "src/", "C:/x.py"],
)  # fmt: skip
def test_unsafe_paths_are_refused(client, project, h, folder, path):
    allow_writes(client)
    r = client.post(
        f"/api/projects/{project['id']}/files/preview",
        headers=h,
        json={"path": path, "content": "x"},
    )
    assert r.status_code == 400, (path, r.text)


def test_symlinks_out_of_the_folder_are_refused(client, project, h, folder):
    allow_writes(client)
    os.symlink(OUTSIDE, folder / "link")
    os.symlink(OUTSIDE / "target.txt", folder / "file-link.txt")
    for path in ("link/new.py", "file-link.txt"):
        r = client.post(
            f"/api/projects/{project['id']}/files/write", headers=h,
            json={"path": path, "content": "x", "expected_sha256": None},
        )  # fmt: skip
        assert r.status_code == 400, (path, r.text)
    assert not list(OUTSIDE.iterdir())


def test_binary_and_unconnected(client, project, make_task, h, folder):
    allow_writes(client)
    (folder / "img.bin").write_bytes(b"\x00\x01")
    r = client.post(
        f"/api/projects/{project['id']}/files/preview",
        headers=h,
        json={"path": "img.bin", "content": "x"},
    )
    assert r.status_code == 400
    other = client.post("/api/projects", json={"name": "No folder"}).json()
    r = client.post(
        f"/api/projects/{other['id']}/files/preview",
        headers=h,
        json={"path": "a.py", "content": "x"},
    )
    assert r.status_code == 400 and r.json()["error"]["code"] == "not_connected"
