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


def test_mcp_endpoints(client, project, make_task, repo, token):
    t = make_task(title="Add rate limiting", acceptance_criteria="429 after 100 requests")
    make_task(title="Done already", status="completed")
    connect(client, project, repo)
    h = {"X-Workspace-Token": token}
    ctx = client.get("/api/claude/context", params={"project_dir": str(repo)}, headers=h).json()
    assert ctx["project"] == "Test project" and [x["title"] for x in ctx["open_tasks"]] == [
        "Add rate limiting"
    ]
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
    assert r["matched_tasks"] == ["Add rate limiting"]
    s = client.get("/api/suggestions").json()[0]
    assert s["payload"]["status"] == "in_review" and "PR opened" in s["evidence"]
    client.post(
        "/api/claude/update",
        headers=h,
        json={"project_dir": str(repo), "summary": "Chose Redis", "kind": "decision"},
    )
    assert any(x["kind"] == "decision" for x in client.get("/api/suggestions").json())
    assert (
        client.get("/api/claude/context", params={"project_dir": "/nope"}, headers=h).status_code
        == 404
    )
    client.put(
        f"/api/projects/{project['id']}/connection",
        json={"path": str(repo), "accept_claude": False},
    )
    assert (
        client.get("/api/claude/context", params={"project_dir": str(repo)}, headers=h).status_code
        == 403
    )


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
