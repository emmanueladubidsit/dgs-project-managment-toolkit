"""Connected codebases (read-only git sync), Claude Code hooks and MCP endpoints, privacy."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent / "_tmp_repo"
GIT = [
    "git",
    "-c",
    "user.name=Jane Doe",
    "-c",
    "user.email=jane@example.com",
    "-c",
    "commit.gpgsign=false",
]


def commit(msg: str, file: str = "app.py", content: str | None = None):
    (REPO / file).write_text(content or msg)
    subprocess.run([*GIT, "-C", str(REPO), "add", "-A"], check=True, capture_output=True)
    subprocess.run([*GIT, "-C", str(REPO), "commit", "-m", msg], check=True, capture_output=True)


@pytest.fixture
def repo():
    shutil.rmtree(REPO, ignore_errors=True)
    REPO.mkdir()
    subprocess.run(["git", "-C", str(REPO), "init", "-q", "-b", "main"], check=True)
    commit("Initial commit")
    commit("Add login page", "login.py")
    yield REPO
    shutil.rmtree(REPO, ignore_errors=True)


@pytest.fixture
def token(client):
    return client.get("/api/claude/setup").json()["token"]


def connect(client, project, path):
    return client.put(f"/api/projects/{project['id']}/connection", json={"path": str(path)})


def test_connect_validation(client, project, repo):
    assert connect(client, project, "relative").status_code == 400
    assert connect(client, project, "/").status_code == 400
    r = connect(client, project, repo)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["is_git"] and c["branch"] == "main" and c["uncommitted_changes"] == 0
    other = client.post("/api/projects", json={"name": "Other"}).json()
    assert connect(client, other, repo).status_code == 409  # one project per folder


def test_git_sync_imports_history_then_suggests_from_new_commits(client, project, make_task, repo):
    t = make_task(title="ISSUE-0001: frontend never sends the API key")
    connect(client, project, repo)
    events = client.get(f"/api/projects/{project['id']}/code-events").json()
    assert [e["title"] for e in events] == ["Add login page", "Initial commit"]
    assert events[0]["detail"]["files"] == ["login.py"]
    assert "Jane" not in str(events)  # author names are never stored
    assert client.get("/api/suggestions").json() == []  # history import does not raise suggestions

    commit("Fix ISSUE-0001: send API key header", "api.py")
    (repo / "wip.txt").write_text("uncommitted")
    r = client.post(f"/api/projects/{project['id']}/sync").json()
    assert r["new_commits"] == 1 and r["suggestions"] == 1 and r["uncommitted_changes"] == 1
    s = client.get("/api/suggestions").json()[0]
    assert s["kind"] == "task_update" and s["payload"]["status"] == "completed"
    assert s["payload"]["task_id"] == t["id"] and s["generator"] == "git"
    # Re-syncing does not duplicate the commit or the suggestion
    assert client.post(f"/api/projects/{project['id']}/sync").json()["new_commits"] == 0
    assert len(client.get("/api/suggestions").json()) == 1
    # Approval applies the change, with history
    client.post(f"/api/suggestions/{s['id']}/approve", json={})
    task = client.get(f"/api/tasks/{t['id']}").json()
    assert task["status"] == "completed" and task["completed_at"]
    actions = [a["changes"] for a in client.get(f"/api/tasks/{t['id']}/activity").json()]
    assert any("source" in c and "git" in str(c["source"]) for c in actions)


def test_sync_never_modifies_the_folder(client, project, repo):
    before = sorted(p.name for p in repo.iterdir())
    connect(client, project, repo)
    client.post(f"/api/projects/{project['id']}/sync")
    assert sorted(p.name for p in repo.iterdir()) == before
    st = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
    )
    assert st.stdout == ""


def test_hook_requires_token(client, project, repo):
    connect(client, project, repo)
    r = client.post("/api/claude/events", json={"hook_event_name": "Stop", "cwd": str(repo)})
    assert r.status_code == 401
    r = client.post(
        "/api/claude/events",
        json={"hook_event_name": "Stop"},
        headers={"X-Workspace-Token": "wrong"},
    )
    assert r.status_code == 401


def test_stop_hook_records_session_summary_safely(client, project, repo, token):
    client.put("/api/privacy/names", json=[{"name": "Jane Doe", "replacement": "the reviewer"}])
    connect(client, project, repo)
    h = {"X-Workspace-Token": token, "X-Claude-Project-Dir": str(repo)}
    msg = (
        "Fixed the login bug Jane Doe reported.\nUsed key sk-ant-abcdefghijklmnopqrstuv123 to test."
    )
    for _ in range(2):
        r = client.post(
            "/api/claude/events",
            headers=h,
            json={
                "hook_event_name": "Stop",
                "session_id": "s1",
                "cwd": str(repo / "sub"),
                "last_assistant_message": msg,
            },
        )
        assert r.json()["accepted"] is True
    ev = [
        e
        for e in client.get(f"/api/projects/{project['id']}/code-events?kind=claude_session").json()
    ]
    assert len(ev) == 1 and ev[0]["detail"]["turns"] == 2
    assert "Jane" not in ev[0]["summary"] and "the reviewer" in ev[0]["summary"]
    assert "sk-ant" not in ev[0]["summary"] and "[redacted]" in ev[0]["summary"]
    assert ev[0]["title"] == "Fixed the login bug the reviewer reported."
    # Subagent events and unknown folders are ignored
    assert (
        client.post(
            "/api/claude/events", headers=h, json={"hook_event_name": "Stop", "agent_id": "a"}
        ).json()["accepted"]
        is False
    )
    other = {"X-Workspace-Token": token, "X-Claude-Project-Dir": "/tmp/elsewhere"}
    assert (
        client.post(
            "/api/claude/events",
            headers=other,
            json={"hook_event_name": "Stop", "cwd": "/tmp/elsewhere"},
        ).json()["accepted"]
        is False
    )
    # Save the session as an update
    r = client.post(f"/api/code-events/{ev[0]['id']}/save-as-update")
    assert r.status_code == 201


def test_task_completed_hook_matches_tasks(client, project, make_task, repo, token):
    t = make_task(title="Write the release notes")
    connect(client, project, repo)
    h = {"X-Workspace-Token": token, "X-Claude-Project-Dir": str(repo)}
    r = client.post(
        "/api/claude/events",
        headers=h,
        json={
            "hook_event_name": "TaskCompleted",
            "session_id": "s1",
            "task_subject": "Write the release notes",
        },
    ).json()
    assert r["suggestions"] == 1
    s = client.get("/api/suggestions").json()[0]
    assert (
        s["kind"] == "task_update"
        and s["payload"]["task_id"] == t["id"]
        and s["generator"] == "claude"
    )
    # Unmatched work becomes a progress suggestion, never a silent change
    client.post(
        "/api/claude/events",
        headers=h,
        json={
            "hook_event_name": "TaskCompleted",
            "session_id": "s1",
            "task": {"subject": "Refactor the cache layer"},
        },
    )
    kinds = sorted(x["kind"] for x in client.get("/api/suggestions").json())
    assert kinds == ["progress", "task_update"]
    assert client.get(f"/api/tasks/{t['id']}").json()["status"] == "todo"


def test_mcp_context_is_off_by_default_and_masked(client, project, make_task, repo, token):
    client.put("/api/privacy/names", json=[{"name": "Jane Doe", "replacement": "the reviewer"}])
    t = make_task(
        title="Add rate limiting for Jane Doe", acceptance_criteria="429 after 100 requests"
    )
    make_task(title="Done already", status="completed")
    connect(client, project, repo)
    h = {"X-Workspace-Token": token}
    params = {"project_dir": str(repo)}
    r = client.get("/api/claude/context", params=params, headers=h)
    assert r.status_code == 403 and r.json()["error"]["code"] == "outbound_disabled"
    assert client.get("/api/claude/settings").json() == {
        "allow_outbound": False,
        "allow_file_writes": False,  # browser-extension file writes are off by default too
    }
    client.put("/api/claude/settings", json={"allow_outbound": True})
    ctx = client.get("/api/claude/context", params=params, headers=h).json()
    assert [x["title"] for x in ctx["open_tasks"]] == ["Add rate limiting for the reviewer"]
    # Inbound reports never need outbound sharing
    client.put("/api/claude/settings", json={"allow_outbound": False})
    r = client.post(
        "/api/claude/report",
        headers=h,
        json={
            "project_dir": str(repo),
            "task": t["id"],
            "status": "in_review",
            "note": "PR opened",
        },
    ).json()
    assert len(r["matched_tasks"]) == 1
    s = client.get("/api/suggestions").json()[0]
    assert s["payload"]["status"] == "in_review" and "PR opened" in s["evidence"]
    client.post(
        "/api/claude/update",
        headers=h,
        json={"project_dir": str(repo), "summary": "Chose Redis", "kind": "decision"},
    )
    assert any(x["kind"] == "decision" for x in client.get("/api/suggestions").json())
    client.put("/api/claude/settings", json={"allow_outbound": True})
    assert (
        client.get("/api/claude/context", params={"project_dir": "/nope"}, headers=h).status_code
        == 404
    )
    client.put(
        f"/api/projects/{project['id']}/connection",
        json={"path": str(repo), "accept_claude": False},
    )
    assert client.get("/api/claude/context", params=params, headers=h).status_code == 403


def test_setup_and_disconnect(client, project, repo, token):
    s = client.get("/api/claude/setup").json()
    assert s["token"] == token  # stable
    assert "claude mcp add --scope user dgs-workspace" in s["mcp_command"]
    assert set(s["hook_settings"]["hooks"]) == {"Stop", "SessionEnd", "TaskCompleted"}
    connect(client, project, repo)
    assert client.delete(f"/api/projects/{project['id']}/connection").status_code == 204
    assert repo.exists() and client.get(f"/api/projects/{project['id']}/connection").json() is None


def test_privacy_masks_exports(client):
    client.put("/api/privacy/names", json=[{"name": "Jane Doe", "replacement": "Reviewer"}])
    p = client.post(
        "/api/projects", json={"name": "Masked", "stakeholders": "Jane Doe (lead)"}
    ).json()
    import io

    from docx import Document

    doc = Document(
        io.BytesIO(client.get(f"/api/export/project/{p['id']}/brief?format=docx").content)
    )
    text = "\n".join(x.text for x in doc.paragraphs)
    assert "Jane" not in text and "Reviewer (lead)" in text


# ---------------------------------------------------------------- local progress files
FOLDER = Path(__file__).parent / "_tmp_progress"


@pytest.fixture
def progress_folder():
    shutil.rmtree(FOLDER, ignore_errors=True)
    (FOLDER / ".claude" / "issues").mkdir(parents=True)
    (FOLDER / ".claude" / "history" / "worklog").mkdir(parents=True)
    (FOLDER / "node_modules" / "x").mkdir(parents=True)
    (FOLDER / "PROGRESS.md").write_text(
        "# Progress\n\n| Item | Status |\n|---|---|\n| AEH-001 CI on hosted runner | ✅ Done |\n"
        "| AEH-002 supply chain | Not started |\n\n- [ ] Write the release notes\n"
    )
    (FOLDER / ".claude" / "issues" / "INDEX.md").write_text(
        "| ID | Title | Status |\n|---|---|---|\n| ISSUE-0003 | llm module | Open |\n"
    )
    (FOLDER / ".claude" / "issues" / "ISSUE-0004-thresholds.md").write_text(
        "# Thresholds\n\nStatus: closed\n"
    )
    (FOLDER / "node_modules" / "x" / "PROGRESS.md").write_text("| AEH-002 | Done |")  # ignored
    (FOLDER / ".env").write_text("SECRET=1")
    yield FOLDER
    shutil.rmtree(FOLDER, ignore_errors=True)


def test_progress_files_detected_and_synced_locally(client, project, make_task, progress_folder):
    a1 = make_task(title="AEH-001: CI on a hosted runner")
    a2 = make_task(title="AEH-002: supply-chain controls")
    i3 = make_task(title="ISSUE-0003: llm_provider module missing")
    i4 = make_task(title="ISSUE-0004: appetite thresholds differ")
    notes = make_task(title="Write the release notes")
    c = connect(client, project, progress_folder).json()
    # This folder sits inside the app's own repository: git is scoped to the folder only.
    assert {"**/PROGRESS.md", "**/.claude/issues/*.md"} <= set(c["progress_patterns"])
    assert c["progress_files_tracked"] == 3  # node_modules and .env ignored

    # First sync: only "done in the file, open in the workspace" becomes a suggestion
    sugg = {
        s["payload"]["task_id"]: s["payload"]["status"]
        for s in client.get("/api/suggestions").json()
    }
    assert sugg == {a1["id"]: "completed", i4["id"]: "completed"}

    # Later edits: newly in-progress items, newly ticked checklist items and new worklogs
    (progress_folder / "PROGRESS.md").write_text(
        "# Progress\n\n| Item | Status |\n|---|---|\n| AEH-001 CI on hosted runner | ✅ Done |\n"
        "| AEH-002 supply chain | In progress |\n\n- [x] Write the release notes\n"
    )
    (progress_folder / ".claude" / "history" / "worklog" / "2026-11-22-notes.md").write_text(
        "# Added rate limiting\n\n"
        "Implemented limits; key sk-ant-abcdefghijklmnopqrstuv0 used in tests."
    )
    r = client.post(f"/api/projects/{project['id']}/sync").json()
    assert r["suggestions"] == 2
    sugg = {
        s["payload"]["task_id"]: s["payload"]["status"]
        for s in client.get("/api/suggestions").json()
    }
    assert sugg[a2["id"]] == "in_progress" and sugg[notes["id"]] == "completed"
    assert i3["id"] not in sugg  # "Open" never suggests anything
    events = client.get(f"/api/projects/{project['id']}/code-events?kind=progress_file").json()
    titles = [e["title"] for e in events]
    assert "New worklog: Added rate limiting" in titles and any(
        t.startswith("Updated PROGRESS.md") for t in titles
    )
    worklog = next(e for e in events if e["title"].startswith("New worklog"))
    assert "sk-ant" not in worklog["summary"] and "[redacted]" in worklog["summary"]

    # Unchanged files produce nothing new; files are never modified
    assert client.post(f"/api/projects/{project['id']}/sync").json()["suggestions"] == 0
    assert (progress_folder / ".env").read_text() == "SECRET=1"


def test_progress_pattern_validation(client, project, progress_folder):
    r = client.put(
        f"/api/projects/{project['id']}/connection",
        json={"path": str(progress_folder), "progress_patterns": ["../outside/*.md"]},
    )
    assert r.status_code == 422
    r = client.put(
        f"/api/projects/{project['id']}/connection",
        json={"path": str(progress_folder), "progress_patterns": ["PROGRESS.md"]},
    )
    assert (
        r.json()["progress_patterns"] == ["PROGRESS.md"] and r.json()["progress_files_tracked"] == 1
    )


def test_prose_and_readme_files_never_change_status():
    from app.services.progress_files import SKIP_NAMES, parse

    prose = "- IDs start at `ISSUE-0001` and are never reused, even after an issue is closed."
    assert parse(prose, "notes.md")["ids"] == {}
    assert parse("We fixed AEH-009 last week.", "notes.md")["ids"] == {}
    assert SKIP_NAMES.match("README.md") and SKIP_NAMES.match("_template.md")
    found = parse(
        "- ISSUE-0003: closed\n## AEH-002 — In progress\n| AEH-005 | Not started |", "x.md"
    )
    assert found["ids"] == {"ISSUE-0003": "completed", "AEH-002": "in_progress", "AEH-005": "todo"}
