"""Connected codebases: read-only git sync, Claude Code reports and task matching.

Git is run with fixed argument lists (no shell), a timeout, and only read commands (rev-parse,
status, log). Nothing in the folder is modified. Commit author names are never stored."""

import hashlib
import logging
import os
import re
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CodeEvent, ProjectConnection, Suggestion, Task
from app.models.enums import TaskStatus
from app.models.voice import SuggestionKind, SuggestionStatus
from app.services import files, privacy, text_tools
from app.services.tasks import DONE, now

log = logging.getLogger("app.codebase")
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{1,5}\b")
DONE_WORDS = re.compile(
    r"\b(fix(e[sd])?|close[sd]?|resolve[sd]?|complete[sd]?|done|finish(e[sd])?|implement(s|ed)?)\b",
    re.I,
)
MAX_COMMITS_FIRST_SYNC = 50


class GitError(RuntimeError):
    pass


def git(path: str, *args: str, timeout: int = 15) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C"}
    try:
        r = subprocess.run(
            ["git", "-C", path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GitError(f"git could not run: {e}") from e
    if r.returncode != 0:
        raise GitError(r.stderr.strip()[:300] or "git failed")
    return r.stdout


def is_git_repo(path: str) -> bool:
    try:
        return git(path, "rev-parse", "--is-inside-work-tree").strip() == "true"
    except GitError:
        return False


def find_connection(db: Session, folder: str | None) -> ProjectConnection | None:
    """The connection whose folder contains `folder` (most specific wins)."""
    if not folder:
        return None
    try:
        target = Path(folder).resolve()
    except (OSError, RuntimeError):
        return None
    best = None
    for c in db.scalars(select(ProjectConnection)).unique():
        base = Path(c.path)
        if (target == base or target.is_relative_to(base)) and (
            best is None or len(c.path) > len(best.path)
        ):
            best = c
    return best


# ---------------------------------------------------------------- task matching
def _open_tasks(db: Session, project_id: uuid.UUID) -> list[Task]:
    return list(
        db.scalars(
            select(Task).where(
                Task.project_id == project_id, Task.archived_at.is_(None), Task.status.not_in(DONE)
            )
        )
    )


def match_tasks(db: Session, project_id: uuid.UUID, text: str) -> list[Task]:
    """Tasks referenced by ID (e.g. ISSUE-0001, AEH-051) or with a near-identical title."""
    tasks = _open_tasks(db, project_id)
    ids = set(ID_RE.findall(text))
    by_id = [t for t in tasks if ids & set(ID_RE.findall(t.title))]
    if by_id:
        return by_id
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return [t for t in tasks if text_tools.similar(t.title, first_line)][:1]


def suggest_task_updates(
    db: Session,
    project_id: uuid.UUID,
    text: str,
    evidence: str,
    generator: str,
    source_type: str,
    source_id: uuid.UUID | None,
    force_status: str | None = None,
) -> list[Suggestion]:
    """Create pending 'task_update' suggestions for tasks the text refers to."""
    created = []
    for task in match_tasks(db, project_id, text):
        status = force_status or ("completed" if DONE_WORDS.search(text) else "in_progress")
        if status == "in_progress" and task.status != TaskStatus.TODO:
            continue  # nothing to change
        dup = db.scalar(
            select(Suggestion).where(
                Suggestion.kind == SuggestionKind.TASK_UPDATE,
                Suggestion.status == SuggestionStatus.PENDING,
                Suggestion.payload["task_id"].astext == str(task.id),
                Suggestion.payload["status"].astext == status,
            )
        )
        if dup:
            continue
        s = Suggestion(
            kind=SuggestionKind.TASK_UPDATE,
            source_type=source_type,
            source_id=source_id,
            project_id=project_id,
            generator=generator,
            payload={"task_id": str(task.id), "title": task.title, "status": status},
            evidence=evidence[:2000],
        )
        db.add(s)
        created.append(s)
    return created


# ---------------------------------------------------------------- sync
def _event(db: Session, conn: ProjectConnection, kind: str, ref: str, **fields) -> CodeEvent | None:
    existing = db.scalar(
        select(CodeEvent).where(
            CodeEvent.connection_id == conn.id, CodeEvent.kind == kind, CodeEvent.ref == ref
        )
    )
    if existing:
        return None
    ev = CodeEvent(connection_id=conn.id, project_id=conn.project_id, kind=kind, ref=ref, **fields)
    db.add(ev)
    db.flush()
    return ev


def sync_connection(db: Session, conn: ProjectConnection) -> dict:
    """Refresh git status and record new commits. Returns counts for the caller."""
    result = {"new_commits": 0, "suggestions": 0, "uncommitted_changes": 0, "files_changed": 0}
    if not Path(conn.path).is_dir():
        conn.last_error = "The folder is no longer available at this path."
        conn.last_synced_at = now()
        db.commit()
        return result
    conn.is_git = is_git_repo(conn.path)
    try:
        if conn.is_git:
            conn.branch = git(conn.path, "rev-parse", "--abbrev-ref", "HEAD").strip()[:200]
            try:
                conn.head = git(conn.path, "rev-parse", "HEAD").strip()[:64]
            except GitError:
                conn.head = None  # repository without commits yet
            status = git(conn.path, "status", "--porcelain")
            conn.uncommitted_changes = len([x for x in status.splitlines() if x.strip()])
            result["uncommitted_changes"] = conn.uncommitted_changes
            if conn.head:
                known = db.scalar(
                    select(CodeEvent)
                    .where(CodeEvent.connection_id == conn.id, CodeEvent.kind == "commit")
                    .limit(1)
                )
                n = 200 if known else MAX_COMMITS_FIRST_SYNC
                raw = git(
                    conn.path,
                    "log",
                    f"-n{n}",
                    "--date=iso-strict",
                    "--pretty=format:%x1e%H%x1f%cI%x1f%s",
                    "--name-only",
                )
                for block in raw.split("\x1e"):
                    if not block.strip():
                        continue
                    head, *file_lines = block.strip("\n").split("\n")
                    sha, when, subject = (head.split("\x1f") + ["", "", ""])[:3]
                    files_changed = [f for f in file_lines if f.strip()][:50]
                    subject = privacy.clean(db, subject, 500) or "(no message)"
                    ev = _event(
                        db,
                        conn,
                        "commit",
                        sha,
                        title=subject,
                        detail={
                            "files": files_changed,
                            "file_count": len(file_lines),
                            "branch": conn.branch,
                        },
                        occurred_at=datetime.fromisoformat(when),
                    )
                    if ev:
                        result["new_commits"] += 1
                        if known:  # only suggest from new work, not the initial history import
                            result["suggestions"] += len(
                                suggest_task_updates(
                                    db,
                                    conn.project_id,
                                    subject,
                                    f"Commit {sha[:8]}: {subject}",
                                    "git",
                                    "commit",
                                    ev.id,
                                )
                            )
                        conn.last_activity_at = max(
                            conn.last_activity_at or ev.occurred_at, ev.occurred_at
                        )
        else:
            found, _ = files.scan(conn.path)
            since = conn.last_synced_at
            changed = [f for f in found if since is None or f.modified_at > since]
            result["files_changed"] = len(changed) if since else 0
            if changed and since:
                newest = max(f.modified_at for f in changed)
                _event(
                    db,
                    conn,
                    "files",
                    newest.isoformat(),
                    title=f"{len(changed)} file(s) changed",
                    detail={"files": [f.relative_path for f in changed[:50]]},
                    occurred_at=newest,
                )
                conn.last_activity_at = newest
        conn.last_error = None
    except GitError as e:
        conn.last_error = str(e)
    conn.last_synced_at = now()
    db.commit()
    return result


# ---------------------------------------------------------------- Claude Code reports
def _first_text(payload: dict, keys: list[str]) -> str | None:
    for k in keys:
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            inner = _first_text(v, keys)
            if inner:
                return inner
    return None


def handle_hook(db: Session, payload: dict, project_dir: str | None) -> dict:
    """Process a Claude Code hook payload. Only documented, common fields are relied on; the
    task-completion schema is read defensively because it is not fully documented."""
    event = str(payload.get("hook_event_name") or "")
    conn = find_connection(db, project_dir or payload.get("cwd"))
    if not conn:
        return {"accepted": False, "reason": "No connected project folder for this session."}
    if not conn.accept_claude:
        return {"accepted": False, "reason": "Claude reports are turned off for this project."}
    session = str(payload.get("session_id") or "unknown")[:100]
    if payload.get("agent_id"):
        return {"accepted": False, "reason": "Subagent events are ignored."}
    when = now()
    if event in ("Stop", "SessionEnd"):
        message = privacy.clean(db, _first_text(payload, ["last_assistant_message"]), 3000)
        ev = db.scalar(
            select(CodeEvent).where(
                CodeEvent.connection_id == conn.id,
                CodeEvent.kind == "claude_session",
                CodeEvent.ref == session,
            )
        )
        title = (message or "Claude Code session").splitlines()[0][:200]
        if ev is None:
            ev = CodeEvent(
                connection_id=conn.id,
                project_id=conn.project_id,
                kind="claude_session",
                ref=session,
                title=title,
                summary=message,
                occurred_at=when,
                detail={"turns": 0},
            )
            db.add(ev)
        if message:
            ev.title, ev.summary = title, message
        ev.detail = {
            **(ev.detail or {}),
            "turns": (ev.detail or {}).get("turns", 0) + (event == "Stop"),
            "ended": event == "SessionEnd" or (ev.detail or {}).get("ended", False),
        }
        ev.occurred_at = when
        conn.last_activity_at = when
        db.commit()
        return {"accepted": True, "event": event}
    if event == "TaskCompleted":
        text = _first_text(
            payload, ["task_subject", "subject", "title", "content", "description", "task"]
        )
        if not text:
            return {"accepted": False, "reason": "No task text in the payload."}
        text = privacy.clean(db, text, 500)
        ref = str(
            payload.get("task_id") or hashlib.sha1(f"{session}:{text}".encode()).hexdigest()[:16]
        )
        ev = _event(
            db,
            conn,
            "claude_task",
            ref,
            title=text,
            summary=None,
            detail={"session_id": session},
            occurred_at=when,
        )
        n = 0
        if ev:
            made = suggest_task_updates(
                db,
                conn.project_id,
                text,
                f"Claude completed: {text}",
                "claude",
                "claude_task",
                ev.id,
                force_status="completed",
            )
            if not made:  # unknown work — offer to record it as a progress update
                db.add(
                    Suggestion(
                        kind=SuggestionKind.PROGRESS,
                        source_type="claude_task",
                        source_id=ev.id,
                        project_id=conn.project_id,
                        generator="claude",
                        payload={"title": f"Claude completed: {text}"},
                        evidence=f"Claude completed: {text}",
                    )
                )
                made = [None]
            n = len(made)
        conn.last_activity_at = when
        db.commit()
        return {"accepted": True, "event": event, "suggestions": n}
    return {"accepted": False, "reason": f"Event {event or 'unknown'} is not used."}


def report_from_claude(
    db: Session,
    conn: ProjectConnection,
    task_ref: str,
    status: str,
    note: str | None,
    session: str | None,
) -> dict:
    """An explicit report from the MCP tool: always a suggestion awaiting approval."""
    text = privacy.clean(db, task_ref, 300) or ""
    note = privacy.clean(db, note, 2000)
    ref = hashlib.sha1(f"{session}:{text}:{status}:{note}".encode()).hexdigest()[:16]
    ev = _event(
        db,
        conn,
        "claude_task",
        ref,
        title=f"{text} → {status}",
        summary=note,
        detail={"session_id": session, "status": status},
        occurred_at=now(),
    )
    tasks = []
    try:
        t = db.get(Task, uuid.UUID(task_ref))
        if t and t.project_id == conn.project_id:
            tasks = [t]
    except ValueError:
        tasks = match_tasks(db, conn.project_id, text)
    created = []
    for t in tasks[:3]:
        created += suggest_task_updates(
            db,
            conn.project_id,
            t.title,
            f"Claude reported “{text}” as {status}" + (f": {note}" if note else ""),
            "claude",
            "claude_task",
            ev.id if ev else None,
            force_status=status,
        )
    if not tasks:
        db.add(
            Suggestion(
                kind=SuggestionKind.PROGRESS,
                source_type="claude_task",
                source_id=ev.id if ev else None,
                project_id=conn.project_id,
                generator="claude",
                payload={"title": f"Claude: {text} ({status})"},
                evidence=note or text,
            )
        )
    conn.last_activity_at = now()
    db.commit()
    return {
        "matched_tasks": [t.title for t in tasks[:3]],
        "suggestions": max(len(created), 0 if tasks else 1),
    }


def utc_iso(dt: datetime | None) -> str | None:
    return dt.astimezone(UTC).isoformat() if dt else None
