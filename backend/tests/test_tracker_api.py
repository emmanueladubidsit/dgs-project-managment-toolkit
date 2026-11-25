"""Tracker refresh → review → approval, the projects folder, discovery and new projects."""

import shutil
from pathlib import Path

import pytest

HERE = Path(__file__).parent
FOLDER = HERE / "_tmp_tracker"
ROOT = HERE / "_tmp_projects"
TRACKER = FOLDER / "docs" / "project-management" / "PROGRESS-AND-PLAN-2026-11-25.md"

TEXT = """# Progress report (written Wed 25 Nov 2026)

## 1. Week 1 (Mon 16 to Fri 20 Nov)

| Day | What was done | Evidence |
|---|---|---|
| Wed 18 | Current and expected architecture diagrams drawn (8 groups). Questionnaire review workbook. ISSUE-0007 fixed. ISSUE-0009 logged. | wl |
| Sat 21 | Admin bulk upload. | wl |

**Week 1 milestone ("baseline and scope"):**
- Implementation baseline established: **Verified**
- MVP scope approved: **In progress**

### Week 3 (30 Nov to 4 Dec), M3: identity and access
| Day | Task |
|---|---|
| Mon 30 | Login and session handling. |
| Tue 1 | Protect all routes (ISSUE-0001). |
"""


@pytest.fixture
def folder():
    shutil.rmtree(FOLDER, ignore_errors=True)
    TRACKER.parent.mkdir(parents=True)
    TRACKER.write_text(TEXT)
    yield FOLDER
    shutil.rmtree(FOLDER, ignore_errors=True)


def connect(client, project, path):
    r = client.put(f"/api/projects/{project['id']}/connection", json={"path": str(path)})
    assert r.status_code == 200, r.text
    return r.json()


def pending(client, project):
    rows = client.get("/api/suggestions", params={"project_id": project["id"]}).json()
    return [s for s in rows if s["generator"] == "tracker"]


def tasks(client, project):
    return client.get("/api/tasks", params={"project_id": project["id"]}).json()


def test_refresh_requires_a_connection(client, project):
    r = client.post(f"/api/projects/{project['id']}/tracker/refresh")
    assert r.status_code == 400 and r.json()["error"]["code"] == "not_connected"


def test_refresh_proposes_and_matches_without_changing_anything(client, project, make_task, folder):
    diagrams = make_task(title="Current and expected architecture diagrams")
    fixed = make_task(title="ISSUE-0007: report export cannot authenticate")
    logged = make_task(title="ISSUE-0009: secrets in environment variables")
    issue = make_task(
        title="ISSUE-0001: frontend never sends the API key", scheduled_date="2026-11-23"
    )
    c = connect(client, project, folder)  # connecting runs the first refresh
    assert c["tracker_file"] == "docs/project-management/PROGRESS-AND-PLAN-2026-11-25.md"
    sugg = pending(client, project)
    kinds = sorted(s["kind"] for s in sugg)
    assert kinds.count("milestone") == 2  # Week 1 and M3
    assert kinds.count("progress") == 2  # Wed 18 and Mon 23 (Saturday's work)
    updates = {s["payload"]["task_id"]: s for s in sugg if s["kind"] == "task_update"}
    # Work on a task ID closes it; an issue that was only "logged" is not progress on it.
    assert updates[fixed["id"]]["payload"]["status"] == "completed"
    assert logged["id"] not in updates
    # Planned work on an open task proposes its day and milestone, without a status change.
    plan = updates[issue["id"]]["payload"]
    assert (plan["status"], plan["scheduled_date"]) == ("todo", "2026-12-01")
    assert plan["current_scheduled_date"] == "2026-11-23"  # proposed as a reschedule
    new = {s["payload"]["title"]: s for s in sugg if s["kind"] == "task"}
    assert not any("ISSUE-0001" in t for t in new)
    # A loose title match is a new task flagged as possibly the same, never a silent match.
    loose = new["Current and expected architecture diagrams drawn (8 groups)"]
    assert loose["duplicate_of_task_id"] == diagrams["id"]
    assert "Questionnaire review workbook" in new and "Login and session handling" in new
    sat = new["Admin bulk upload"]
    assert sat["payload"]["item_date"] == "2026-11-23"
    assert sat["payload"]["original_date"] == "2026-11-21"
    # Nothing changed yet (ADR 0002).
    assert {t["id"]: t["status"] for t in tasks(client, project)}[fixed["id"]] == "todo"

    # A second refresh proposes nothing new.
    r = client.post(f"/api/projects/{project['id']}/tracker/refresh").json()
    assert r["milestones"] == r["tasks"] == r["updates"] == r["work_logs"] == 0
    assert r["pending"] == len(sugg)


def test_approve_all_applies_statuses_milestones_and_dates(client, project, make_task, folder):
    existing = make_task(title="ISSUE-0007: report export cannot authenticate")
    issue = make_task(title="ISSUE-0001: frontend never sends the API key")
    connect(client, project, folder)
    sugg = pending(client, project)
    r = client.post(
        "/api/suggestions/approve-batch", json={"items": [{"id": s["id"]} for s in sugg]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["failed"] == 0, r.json()
    ms = {
        m["title"]: m
        for m in client.get("/api/milestones", params={"project_id": project["id"]}).json()
    }
    assert ms["Week 1 milestone: baseline and scope"]["status"] == "in_progress"
    assert ms["M3: identity and access"]["due_date"] == "2026-12-01"
    by_title = {t["title"]: t for t in tasks(client, project)}
    done = by_title["ISSUE-0007: report export cannot authenticate"]
    assert done["id"] == existing["id"] and done["status"] == "completed"
    assert done["completed_at"].startswith("2026-11-18")  # dated to the working day
    scheduled = by_title["ISSUE-0001: frontend never sends the API key"]
    assert scheduled["id"] == issue["id"] and scheduled["status"] == "todo"
    assert scheduled["scheduled_date"] == "2026-12-01"
    assert scheduled["milestone_id"] == ms["M3: identity and access"]["id"]
    assert "Current and expected architecture diagrams drawn (8 groups)" in by_title
    login = by_title["Login and session handling"]
    assert login["status"] == "todo" and login["scheduled_date"] == "2026-11-30"
    assert login["milestone_id"] == ms["M3: identity and access"]["id"]
    baseline = by_title["Implementation baseline established"]
    assert baseline["status"] == "completed"
    assert baseline["milestone_id"] == ms["Week 1 milestone: baseline and scope"]["id"]
    assert by_title["MVP scope approved"]["status"] == "in_progress"
    logs = client.get("/api/work-logs", params={"project_id": project["id"]}).json()
    assert {w["entry_date"] for w in logs} == {"2026-11-18", "2026-11-23"}
    assert any("weekend work from Sat 21 Nov" in w["summary"] for w in logs)

    # The tracker moves an item forward: exactly one update is proposed.
    TRACKER.write_text(TEXT.replace("approved: **In progress**", "approved: **Verified**"))
    r = client.post(f"/api/projects/{project['id']}/tracker/refresh").json()
    assert (r["tasks"], r["updates"]) == (0, 1)
    upd = next(s for s in pending(client, project) if s["kind"] == "task_update")
    assert upd["payload"]["task_id"] == by_title["MVP scope approved"]["id"]
    assert upd["payload"]["status"] == "completed"


def test_approval_carries_reviewer_edits(client, project, make_task, folder):
    make_task(title="ISSUE-0007: report export cannot authenticate")
    other_ms = client.post(
        f"/api/projects/{project['id']}/milestones", json={"title": "Chosen by me"}
    ).json()
    ws = client.get(f"/api/projects/{project['id']}/workstreams").json()[0]
    connect(client, project, folder)
    s = next(
        x
        for x in pending(client, project)
        if x["payload"].get("title") == "Login and session handling"
    )
    r = client.post(
        f"/api/suggestions/{s['id']}/approve",
        json={
            "title": "Login (SSO) and sessions",
            "status": "in_progress",
            "progress": 40,
            "milestone_id": other_ms["id"],
            "workstream_id": ws["id"],
            "scheduled_date": "2026-12-02",
        },
    )
    assert r.status_code == 200, r.text
    t = next(x for x in tasks(client, project) if x["title"] == "Login (SSO) and sessions")
    assert (t["status"], t["progress"], t["milestone_id"], t["workstream_id"]) == (
        "in_progress",
        40,
        other_ms["id"],
        ws["id"],
    )
    assert t["scheduled_date"] == "2026-12-02"
    # Task update edits go through history too.
    # Edits on a status update (here: choosing the milestone) are applied with history.
    upd = next(x for x in pending(client, project) if x["kind"] == "task_update")
    r = client.post(f"/api/suggestions/{upd['id']}/approve", json={"milestone_id": other_ms["id"]})
    assert r.status_code == 200, r.text
    t = next(x for x in tasks(client, project) if x["id"] == upd["payload"]["task_id"])
    assert t["status"] == "completed" and t["milestone_id"] == other_ms["id"]
    history = client.get(f"/api/tasks/{t['id']}/activity").json()
    assert any("milestone_id" in (h.get("changes") or {}) for h in history)
    bad = next(x for x in pending(client, project) if x["kind"] == "task")
    r = client.post(f"/api/suggestions/{bad['id']}/approve", json={"status": "bogus"})
    assert r.status_code == 400


def test_rejected_items_are_not_proposed_again(client, project, folder):
    connect(client, project, folder)
    for s in pending(client, project):
        client.post(f"/api/suggestions/{s['id']}/reject")
    r = client.post(f"/api/projects/{project['id']}/tracker/refresh").json()
    assert r["pending"] == 0 and r["tasks"] == 0


def test_missing_tracker_is_reported(client, project, folder):
    TRACKER.unlink()
    c = connect(client, project, folder)
    assert c["tracker_file"] is None and "No tracker found" in c["tracker_warnings"][0]


# ---------------------------------------------------------------- projects folder & discovery
@pytest.fixture
def projects_root(client):
    shutil.rmtree(ROOT, ignore_errors=True)
    r = client.put("/api/settings/projects", json={"root": str(ROOT)})
    assert r.status_code == 400 and r.json()["error"]["code"] == "missing_folder"
    r = client.put("/api/settings/projects", json={"root": str(ROOT), "create": True})
    assert r.status_code == 200, r.text
    assert r.json()["exists"]
    yield ROOT
    shutil.rmtree(ROOT, ignore_errors=True)


def test_projects_folder_validation(client):
    assert client.put("/api/settings/projects", json={"root": "relative/path"}).status_code == 400
    assert client.put("/api/settings/projects", json={"root": "/"}).status_code == 400


def test_discover_and_add_projects(client, projects_root):
    (projects_root / "alpha" / ".git").mkdir(parents=True)
    (projects_root / "alpha" / "README.md").write_text("# Alpha Service\n")
    (projects_root / "group" / "beta").mkdir(parents=True)
    (projects_root / "group" / "beta" / "CLAUDE.md").write_text("x")
    (projects_root / "notes").mkdir()  # not a project
    (projects_root / "node_modules" / "pkg").mkdir(parents=True)
    (projects_root / "node_modules" / "pkg" / "package.json").write_text("{}")
    d = client.get("/api/project-discovery").json()
    found = {c["relative_path"]: c for c in d["candidates"]}
    assert set(found) == {"alpha", "group/beta"}
    assert found["alpha"]["name"] == "Alpha Service" and found["alpha"]["is_git"]
    r = client.post("/api/project-discovery/add", json={"path": found["alpha"]["path"]})
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "Alpha Service"
    d = client.get("/api/project-discovery").json()
    assert [c["relative_path"] for c in d["candidates"]] == ["group/beta"]
    assert d["connected"] == 1
    # Only folders inside the projects folder can be added this way.
    assert client.post("/api/project-discovery/add", json={"path": str(HERE)}).status_code == 400


def test_start_project_creates_tracker_without_overwriting(client, projects_root):
    r = client.post("/api/project-discovery/start", json={"name": "Gamma Tool"})
    assert r.status_code == 201, r.text
    target = projects_root / "Gamma-Tool"
    assert (target / "CLAUDE.md").read_text().startswith("# Gamma Tool")
    trackers = list((target / "docs" / "project-management").glob("PROGRESS-AND-PLAN-*.md"))
    assert len(trackers) == 1 and "Working days" in trackers[0].read_text()
    conn = client.get(f"/api/projects/{r.json()['project_id']}/connection").json()
    assert conn["tracker_file"] and conn["tracker_warnings"] == []
    # The folder now has content: starting again with the same name is refused.
    again = client.post("/api/project-discovery/start", json={"name": "Gamma Tool"})
    assert again.status_code == 409
    assert (target / "CLAUDE.md").read_text().startswith("# Gamma Tool")


def test_instructions_for_existing_projects(client):
    r = client.get("/api/tracker/instructions").json()
    assert "Monday to Friday" in r["claude_md"] and r["tracker_dir"] == "docs/project-management"
