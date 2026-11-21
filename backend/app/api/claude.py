"""Connected codebases, Claude Code integration (hooks + MCP) and privacy settings.

Endpoints called by Claude Code (hooks and the MCP server) require the workspace token in the
`X-Workspace-Token` header, so other local programs cannot post fake progress."""

import hmac
import secrets
import sys
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Body, Depends, Header, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError, bad_request, conflict, not_found
from app.models import CodeEvent, Project, ProjectConnection, Task, WorkLog
from app.models.enums import WorkLogKind
from app.models.system import SystemSetting
from app.models.voice import Suggestion, SuggestionKind
from app.services import codebase, files, privacy
from app.services.tasks import DONE

router = APIRouter(tags=["claude"])
BACKEND_DIR = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- token
def workspace_token(db: Session) -> str:
    row = db.get(SystemSetting, "claude")
    if row and (row.value or {}).get("token"):
        return row.value["token"]
    token = secrets.token_urlsafe(32)
    row = row or SystemSetting(key="claude", value={})
    row.value = {**(row.value or {}), "token": token}
    db.add(row)
    db.commit()
    return token


def require_token(
    x_workspace_token: str | None = Header(default=None), db: Session = Depends(get_db)
) -> None:
    if not x_workspace_token or not hmac.compare_digest(x_workspace_token, workspace_token(db)):
        raise AppError(401, "invalid_token", "Missing or invalid workspace token.")


# ---------------------------------------------------------------- schemas
class ConnectionIn(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    accept_claude: bool = True
    auto_sync: bool = True


class ConnectionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    path: str
    available: bool
    is_git: bool
    accept_claude: bool
    auto_sync: bool
    branch: str | None
    head: str | None
    uncommitted_changes: int
    last_synced_at: str | None
    last_activity_at: str | None
    last_error: str | None


class EventOut(BaseModel):
    id: uuid.UUID
    kind: str
    ref: str
    title: str
    summary: str | None
    detail: dict
    occurred_at: str


def _out(c: ProjectConnection) -> ConnectionOut:
    iso = lambda d: d.isoformat() if d else None  # noqa: E731
    return ConnectionOut(
        id=c.id,
        project_id=c.project_id,
        project_name=c.project.name,
        path=c.path,
        available=Path(c.path).is_dir(),
        is_git=c.is_git,
        accept_claude=c.accept_claude,
        auto_sync=c.auto_sync,
        branch=c.branch,
        head=c.head,
        uncommitted_changes=c.uncommitted_changes,
        last_synced_at=iso(c.last_synced_at),
        last_activity_at=iso(c.last_activity_at),
        last_error=c.last_error,
    )


def _conn(db: Session, project_id: uuid.UUID) -> ProjectConnection:
    c = db.scalar(select(ProjectConnection).where(ProjectConnection.project_id == project_id))
    if not c:
        raise not_found("Connected folder")
    return c


# ---------------------------------------------------------------- connections
@router.get("/connections", response_model=list[ConnectionOut])
def list_connections(db: Session = Depends(get_db)):
    return [_out(c) for c in db.scalars(select(ProjectConnection)).unique()]


@router.get("/projects/{project_id}/connection", response_model=ConnectionOut | None)
def get_connection(project_id: uuid.UUID, db: Session = Depends(get_db)):
    c = db.scalar(select(ProjectConnection).where(ProjectConnection.project_id == project_id))
    return _out(c) if c else None


@router.put("/projects/{project_id}/connection", response_model=ConnectionOut)
def connect(project_id: uuid.UUID, body: ConnectionIn, db: Session = Depends(get_db)):
    """Connect (or change) the project's codebase folder. Read only; runs a first sync."""
    if not db.get(Project, project_id):
        raise not_found("Project")
    try:
        real = str(files.validate_root(body.path))
    except files.PathError as e:
        raise bad_request(str(e), code="invalid_path") from e
    other = db.scalar(
        select(ProjectConnection).where(
            ProjectConnection.path == real, ProjectConnection.project_id != project_id
        )
    )
    if other:
        raise conflict(f"That folder is already connected to “{other.project.name}”.")
    c = db.scalar(select(ProjectConnection).where(ProjectConnection.project_id == project_id))
    if c and c.path != real:
        for ev in db.scalars(select(CodeEvent).where(CodeEvent.connection_id == c.id)):
            db.delete(ev)  # history belonged to the previous folder
        c.head = c.branch = c.last_synced_at = c.last_activity_at = None
    c = c or ProjectConnection(project_id=project_id, path=real)
    c.path, c.accept_claude, c.auto_sync = real, body.accept_claude, body.auto_sync
    db.add(c)
    db.commit()
    codebase.sync_connection(db, c)
    db.refresh(c)
    return _out(c)


@router.delete("/projects/{project_id}/connection", status_code=204)
def disconnect(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Stops watching the folder and removes its activity history. Files are not touched."""
    db.delete(_conn(db, project_id))
    db.commit()
    return Response(status_code=204)


@router.post("/projects/{project_id}/sync")
def sync_now(project_id: uuid.UUID, db: Session = Depends(get_db)):
    c = _conn(db, project_id)
    result = codebase.sync_connection(db, c)
    db.refresh(c)
    return {**result, "connection": _out(c)}


@router.get("/projects/{project_id}/code-events", response_model=list[EventOut])
def code_events(
    project_id: uuid.UUID,
    kind: str | None = None,
    limit: int = Query(default=60, le=300),
    db: Session = Depends(get_db),
):
    stmt = select(CodeEvent).where(CodeEvent.project_id == project_id)
    if kind:
        stmt = stmt.where(CodeEvent.kind == kind)
    rows = db.scalars(stmt.order_by(CodeEvent.occurred_at.desc()).limit(limit))
    return [
        EventOut(
            id=e.id,
            kind=e.kind,
            ref=e.ref,
            title=e.title,
            summary=e.summary,
            detail=e.detail,
            occurred_at=e.occurred_at.isoformat(),
        )
        for e in rows
    ]


@router.post("/code-events/{event_id}/save-as-update", status_code=201)
def save_event_as_update(event_id: uuid.UUID, db: Session = Depends(get_db)):
    """Record a Claude session summary or commit as a project progress update."""
    ev = db.get(CodeEvent, event_id)
    if not ev:
        raise not_found("Activity")
    summary = ev.summary or ev.title
    label = "Claude Code session" if ev.kind == "claude_session" else "Commit"
    log = WorkLog(
        entry_date=ev.occurred_at.date(),
        kind=WorkLogKind.PROGRESS,
        summary=f"{label}: {summary}",
        project_id=ev.project_id,
    )
    db.add(log)
    db.commit()
    return {"work_log_id": str(log.id)}


# ---------------------------------------------------------------- Claude Code setup
@router.get("/claude/setup")
def setup(db: Session = Depends(get_db)):
    """Everything needed to connect Claude Code: hook settings, MCP command and instructions."""
    token = workspace_token(db)
    url = "http://127.0.0.1:8010/api/claude/events"
    curl = (
        f"curl -s -m 3 -X POST {url} -H 'Content-Type: application/json' "
        f"-H 'X-Workspace-Token: {token}' -H \"X-Claude-Project-Dir: $CLAUDE_PROJECT_DIR\" "
        "--data-binary @- >/dev/null 2>&1 || true"
    )
    hook = {"type": "command", "command": curl, "timeout": 5}
    hooks = {"hooks": {e: [{"hooks": [hook]}] for e in ("Stop", "SessionEnd", "TaskCompleted")}}
    mcp_cmd = (
        f"claude mcp add --scope user dgs-workspace -e DGS_WORKSPACE_TOKEN={token} -- "
        f'uv run --directory "{BACKEND_DIR}" python -m app.mcp_server'
    )
    return {
        "token": token,
        "hook_settings": hooks,
        "mcp_command": mcp_cmd,
        "claude_md": (
            "## Workspace progress\nThis folder is connected to the DGS Engineering Workspace. "
            "At the start of a session, call the `dgs-workspace` tool `list_open_tasks` to see "
            "planned work. When you finish or make progress on one of those tasks, call "
            "`report_task_progress` with the task and a one-sentence note. Reports are "
            "reviewed by the user before anything changes."
        ),
        "python": sys.executable,
    }


@router.post("/claude/events", dependencies=[Depends(require_token)])
def claude_event(
    payload: dict = Body(...),
    x_claude_project_dir: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Receives Claude Code hook payloads (Stop, SessionEnd, TaskCompleted)."""
    return codebase.handle_hook(db, payload, x_claude_project_dir or None)


# ---------------------------------------------------------------- MCP server support
class ReportIn(BaseModel):
    project_dir: str
    task: str = Field(min_length=1, max_length=500)
    status: Literal["in_progress", "in_review", "blocked", "completed"] = "completed"
    note: str | None = Field(default=None, max_length=4000)
    session_id: str | None = None


class UpdateIn(BaseModel):
    project_dir: str
    summary: str = Field(min_length=1, max_length=4000)
    kind: Literal["progress", "decision", "blocker"] = "progress"


def _for_dir(db: Session, project_dir: str) -> ProjectConnection:
    c = codebase.find_connection(db, project_dir)
    if not c:
        raise not_found("A connected workspace project for this folder")
    if not c.accept_claude:
        raise AppError(403, "claude_disabled", "Claude reports are turned off for this project.")
    return c


@router.get("/claude/context", dependencies=[Depends(require_token)])
def mcp_context(project_dir: str, db: Session = Depends(get_db)):
    c = _for_dir(db, project_dir)
    tasks = db.scalars(
        select(Task)
        .where(
            Task.project_id == c.project_id, Task.archived_at.is_(None), Task.status.not_in(DONE)
        )
        .order_by(Task.position)
    )
    return {
        "project": c.project.name,
        "open_tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status.value,
                "priority": t.priority.value,
                "milestone": t.milestone.title if t.milestone else None,
                "acceptance_criteria": t.acceptance_criteria,
            }
            for t in tasks
        ][:150],
    }


@router.post("/claude/report", dependencies=[Depends(require_token)])
def mcp_report(body: ReportIn, db: Session = Depends(get_db)):
    c = _for_dir(db, body.project_dir)
    return codebase.report_from_claude(db, c, body.task, body.status, body.note, body.session_id)


@router.post("/claude/update", dependencies=[Depends(require_token)])
def mcp_update(body: UpdateIn, db: Session = Depends(get_db)):
    c = _for_dir(db, body.project_dir)
    kind = {
        "progress": SuggestionKind.PROGRESS,
        "decision": SuggestionKind.DECISION,
        "blocker": SuggestionKind.BLOCKER,
    }[body.kind]
    text = privacy.clean(db, body.summary, 4000)
    db.add(
        Suggestion(
            kind=kind,
            source_type="claude",
            project_id=c.project_id,
            generator="claude",
            payload={"title": text[:300]},
            evidence=text,
        )
    )
    db.commit()
    return {"queued_for_review": True}


# ---------------------------------------------------------------- privacy
class NameRule(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    replacement: str = Field(default="a colleague", max_length=120)


@router.get("/privacy/names", response_model=list[NameRule])
def get_names(db: Session = Depends(get_db)):
    return privacy.name_rules(db)


@router.put("/privacy/names", response_model=list[NameRule])
def put_names(body: list[NameRule], db: Session = Depends(get_db)):
    return privacy.save_name_rules(db, [r.model_dump() for r in body])
