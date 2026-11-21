"""Seed real projects from JSON specs in backend/data/seed/projects/*.json (git-ignored, because
they describe your own work). Run: `uv run python -m app.seed_projects` (or `make seed-projects`).

Everything goes through the app's own API (validation, history and duplicate rules apply).
Idempotent: a project whose name already exists is skipped. Folder registration is read-only.

Spec format (all keys optional except project.name):
{
  "project": {ProjectCreate fields..., "workstreams": ["..."]},
  "stage": "Development",
  "milestones": [{"key": "m1", "title": "...", "due_date": "YYYY-MM-DD", "status": "planned",
                  "deliverables": "...", "description": "..."}],
  "tasks": [{"title": "...", "status": "todo", "priority": "medium", "milestone": "m1",
             "workstream": "Backend/API development", "progress": 0, "due_date": null,
             "description": "...", "acceptance_criteria": "...", "estimate_hours": null,
             "labels": [], "completed_on": "YYYY-MM-DD (for completed work)",
             "subtasks": [{...same fields...}]}],
  "work_logs": [{"entry_date": "YYYY-MM-DD", "kind": "decision", "summary": "..."}],
  "knowledge": [{"category": "...", "title": "...", "summary": "...", "fields": {},
                 "verification": "...", "sources": "...", "tags": []}],
  "documents": [{"root_name": "...", "path": "/abs/folder", "files": ["relative/path.md"]}],
  "links": [{"title": "...", "url": "https://...", "category": "design"}]
}
"""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed" / "projects"


class SeedError(RuntimeError):
    pass


def _ok(r, what: str) -> dict:
    if r.status_code >= 400:
        try:
            msg = r.json()["error"]["message"]
        except Exception:  # noqa: BLE001
            msg = r.text[:200]
        raise SeedError(f"{what}: {msg}")
    return r.json() if r.content else {}


def seed_project(client: TestClient, spec: dict) -> str:
    p = spec["project"]
    name = p["name"]
    existing = client.get("/api/projects", params={"include_archived": True}).json()
    if any(x["name"] == name for x in existing):
        return f"skipped “{name}” (already exists)"

    stages = {s["name"]: s["id"] for s in client.get("/api/stages").json()}
    body = {**p}
    if spec.get("stage"):
        body["stage_id"] = stages.get(spec["stage"])
    project = _ok(client.post("/api/projects", json=body), f"project {name}")
    pid = project["id"]
    ws = {w["name"]: w["id"] for w in client.get(f"/api/projects/{pid}/workstreams").json()}

    ms_ids: dict[str, str] = {}
    for m in spec.get("milestones", []):
        key = m.get("key") or m["title"]
        fields = {
            k: v
            for k, v in m.items()
            if k in {"title", "due_date", "status", "deliverables", "description"}
        }
        if m.get("workstream"):
            fields["workstream_id"] = ws.get(m["workstream"])
        ms_ids[key] = _ok(
            client.post(f"/api/projects/{pid}/milestones", json=fields), f"milestone {m['title']}"
        )["id"]

    task_fields = {
        "title",
        "description",
        "status",
        "priority",
        "start_date",
        "due_date",
        "scheduled_date",
        "estimate_hours",
        "actual_hours",
        "progress",
        "weight",
        "acceptance_criteria",
        "deliverables",
        "labels",
        "notes",
    }
    n_tasks = 0
    historic: list[tuple[str, str | None]] = []

    def make_task(t: dict, parent_id: str | None = None) -> None:
        nonlocal n_tasks
        body = {k: v for k, v in t.items() if k in task_fields and v is not None}
        body["project_id"] = pid
        if parent_id:
            body["parent_id"] = parent_id
        if t.get("milestone"):
            body["milestone_id"] = ms_ids.get(t["milestone"])
        if t.get("workstream"):
            body["workstream_id"] = ws.get(t["workstream"])
        created = _ok(client.post("/api/tasks", json=body), f"task {t['title']}")
        n_tasks += 1
        if body.get("status") == "completed":
            historic.append((created["id"], t.get("completed_on")))
        for sub in t.get("subtasks", []):
            make_task(
                {
                    **sub,
                    "milestone": sub.get("milestone", t.get("milestone")),
                    "workstream": sub.get("workstream", t.get("workstream")),
                },
                created["id"],
            )

    for t in spec.get("tasks", []):
        make_task(t)

    # Work done before import must not appear as "completed today" in reports: use the recorded
    # date when known, otherwise the project's start date (or the day before import).
    if historic:
        _backdate(historic, p.get("start_date"))

    for w in spec.get("work_logs", []):
        _ok(client.post("/api/work-logs", json={**w, "project_id": pid}), "work log")

    for k in spec.get("knowledge", []):
        _ok(
            client.post("/api/knowledge", json={**k, "origin_project_id": pid}),
            f"knowledge {k['title']}",
        )

    for link in spec.get("links", []):
        _ok(
            client.post("/api/documents", json={**link, "project_id": pid}), f"link {link['title']}"
        )

    docs_note = ""
    roots_spec = spec.get("documents") or []
    if isinstance(roots_spec, dict):
        roots_spec = [roots_spec]
    for d in roots_spec:
        if not d.get("path"):
            continue
        roots = client.get("/api/document-roots").json()
        real = str(Path(d["path"]).resolve())
        root = next((r for r in roots if r["path"] == real), None)
        if not root:
            body = {"name": d.get("root_name", name), "path": d["path"], "project_id": pid}
            root = _ok(client.post("/api/document-roots", json=body), f"folder {d['path']}")
        wanted = [f for f in d.get("files", []) if (Path(real) / f).is_file()]
        missing = len(d.get("files", [])) - len(wanted)
        if wanted:
            body = {"paths": wanted, "project_id": pid}
            docs = _ok(client.post(f"/api/document-roots/{root['id']}/register", json=body), "docs")
            docs_note += f", {len(docs)} document(s) indexed from “{root['name']}”"
        if missing:
            docs_note += f" ({missing} listed file(s) not found and skipped)"
    return (
        f"created “{name}”: {len(ms_ids)} milestone(s), {n_tasks} task(s), "
        f"{len(spec.get('work_logs', []))} update(s), {len(spec.get('knowledge', []))} "
        f"knowledge item(s){docs_note}"
    )


def _backdate(items: list[tuple[str, str | None]], fallback: str | None) -> None:
    import uuid
    from datetime import date, datetime, time, timedelta

    from app.db import SessionLocal
    from app.models import Task

    tz = datetime.now().astimezone().tzinfo
    default = date.fromisoformat(fallback) if fallback else date.today() - timedelta(days=1)
    with SessionLocal() as db:
        for tid, when in items:
            task = db.get(Task, uuid.UUID(tid))
            day = date.fromisoformat(when) if when else default
            task.completed_at = datetime.combine(day, time(17, 0), tzinfo=tz)
        db.commit()


def main() -> int:
    from app.main import app

    files = sorted(SEED_DIR.glob("*.json"))
    if not files:
        print(f"No seed specs found in {SEED_DIR}")
        return 0
    with TestClient(app) as client:
        for f in files:
            try:
                print(f"{f.name}: {seed_project(client, json.loads(f.read_text()))}")
            except SeedError as e:
                print(f"{f.name}: FAILED — {e}")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
