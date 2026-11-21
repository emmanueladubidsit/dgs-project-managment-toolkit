"""Local progress records: read status from files that already live in a connected folder
(e.g. PROGRESS.md, .claude/issues/INDEX.md, worklogs, backlogs, CHANGELOG.md).

Nothing is configured in Claude Code and nothing leaves this computer: the workspace only reads
these files (read-only, secret files skipped, size-limited) and turns status changes into
suggestions for approval."""

import fnmatch
import hashlib
import os
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import CodeEvent, ProjectConnection
from app.services import files, privacy
from app.services.tasks import now

DEFAULT_PATTERNS = [
    "**/PROGRESS.md",
    "**/STATUS.md",
    "**/TODO.md",
    "**/CHANGELOG.md",
    "**/WORKPLAN.md",
    "**/.claude/issues/*.md",
    "**/.claude/history/worklog/*.md",
    "**/.claude/history/timeline.md",
    "**/backlog.md",
    "**/backlog/*.md",
    "**/issues/*.md",
]
MAX_FILES = 150
MAX_BYTES = 512 * 1024
MAX_DEPTH = 7
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{1,5}\b")
CHECK_RE = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.+)$")
STATUS_LINE_RE = re.compile(r"(?i)^\W*status\W*[:\-]\s*(.+)$")
# Outside tables, an ID only counts at the start of a line ("- ISSUE-0003: done", "## AEH-1 …"),
# never in the middle of a sentence explaining a convention.
LEADING_ID_RE = re.compile(
    r"^\s*(?:[-*+]|\d+[.)]|#{1,6})?\s*\**\s*`?([A-Z][A-Z0-9]{1,9}-\d{1,5})\b"
)
SKIP_NAMES = re.compile(r"(?i)^(readme|_?template.*|index-template|contributing)\.md$")
WORKLOG_HINT = ("worklog", "history/")

# Order matters: the first matching group wins for a line.
STATUS_WORDS = [
    # Negative phrases first, so "not started" / "not done" are never read as progress.
    (
        "todo",
        re.compile(r"(?i)\b(not (yet )?(started|begun|done|complete[d]?)|incomplete|unfinished)\b"),
    ),
    (
        "completed",
        re.compile(r"(?i)(✅|☑|\b(done|complete[d]?|closed|fixed|resolved|shipped|merged)\b)"),
    ),
    ("in_progress", re.compile(r"(?i)(⏳|🟡|\b(in progress|in-progress|ongoing|started|wip)\b)")),
    ("todo", re.compile(r"(?i)(❌|\b(open|to ?do|planned|backlog)\b)")),
]


def _status_of(text: str) -> str | None:
    for status, rx in STATUS_WORDS:
        if rx.search(text):
            return status
    return None


def _matches(rel: str, pattern: str) -> bool:
    """`**/name` matches at any depth (including the top level)."""
    tail = pattern.removeprefix("**/")
    return (
        fnmatch.fnmatch(rel, pattern)
        or fnmatch.fnmatch(rel, tail)
        or fnmatch.fnmatch("/" + rel, "*/" + tail)
    )


def detect_patterns(root: str) -> list[str]:
    """The default patterns that match at least one file in this folder."""
    found = _walk(root, DEFAULT_PATTERNS)
    return [p for p in DEFAULT_PATTERNS if any(_matches(f, p) for f in found)]


def _walk(root: str, patterns: list[str]) -> list[str]:
    base = Path(root).resolve()
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        rel_dir = Path(dirpath).relative_to(base)
        depth = len(rel_dir.parts)
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in files.SKIP_DIRS
            and depth < MAX_DEPTH
            and (not d.startswith(".") or d == ".claude")
        )
        for name in sorted(filenames):
            rel = str(rel_dir / name) if depth else name
            if files.is_sensitive(name) or SKIP_NAMES.match(name):
                continue
            if any(_matches(rel, p) for p in patterns):
                out.append(rel)
            if len(out) >= MAX_FILES:
                return out
    return out


def parse(text: str, rel_path: str) -> dict:
    """Extract {task_id: status} and checked checklist items from a progress file."""
    ids: dict[str, str] = {}
    checked: list[str] = []
    file_ids = ID_RE.findall(Path(rel_path).name)
    for line in text.splitlines():
        m = CHECK_RE.match(line)
        if m:
            item = m.group(2).strip()
            if m.group(1).lower() == "x":
                checked.append(item[:300])
            for i in ID_RE.findall(item):
                ids[i] = "completed" if m.group(1).lower() == "x" else ids.get(i, "todo")
            continue
        is_row = line.lstrip().startswith("|")
        lead = LEADING_ID_RE.match(line)
        line_ids = ID_RE.findall(line) if is_row else ([lead.group(1)] if lead else [])
        if line_ids:
            st = _status_of(line)
            if st:
                # A row naming several IDs (e.g. "supersedes AEH-002") describes the first one.
                ids[line_ids[0]] = st
        elif file_ids:
            sm = STATUS_LINE_RE.match(line)
            if sm and (st := _status_of(sm.group(1))):
                ids[file_ids[0]] = st
    return {"ids": ids, "checked": checked}


def _summary(text: str) -> tuple[str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = next(
        (ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), lines[0] if lines else ""
    )
    body = " ".join(ln for ln in lines if not ln.startswith("#"))[:600]
    return title[:200], body


def sync_progress_files(db: Session, conn: ProjectConnection, suggest) -> dict:
    """Read the connection's progress files and raise suggestions for status changes.
    `suggest(text, evidence, status)` creates task-update suggestions for matching tasks."""
    patterns = conn.progress_patterns or []
    result = {"progress_files": 0, "status_changes": 0, "suggestions": 0}
    if not patterns:
        return result
    state: dict = dict(conn.file_state or {})
    first_run = not state
    for rel in _walk(conn.path, patterns):
        try:
            path = files.safe_file(conn.path, rel)
            if path.stat().st_size > MAX_BYTES or path.suffix.lower() not in files.TEXT_EXT:
                continue
            text = files.read_text(path)
        except (files.PathError, OSError):
            continue
        result["progress_files"] += 1
        digest = hashlib.sha256(text.encode()).hexdigest()
        prev = state.get(rel) or {}
        if prev.get("hash") == digest:
            continue
        parsed = parse(text, rel)
        prev_ids = prev.get("ids", {})
        prev_checked = set(prev.get("checked", []))
        changes: list[tuple[str, str]] = []
        for tid, st in parsed["ids"].items():
            if prev_ids.get(tid) != st:
                changes.append((tid, st))
        new_checked = [c for c in parsed["checked"] if c not in prev_checked]
        is_new_worklog = not prev and any(h in rel for h in WORKLOG_HINT)
        # Suggestions: completed/in-progress items that the workspace does not yet reflect.
        for tid, st in changes:
            if st == "todo" or (first_run and st != "completed"):
                continue
            label = f"{rel} marks {tid} as {'done' if st == 'completed' else 'in progress'}"
            made = suggest(tid, label, st)
            result["suggestions"] += len(made)
        if not first_run:
            for item in new_checked:
                result["suggestions"] += len(suggest(item, f"{rel}: [x] {item}", "completed"))
        result["status_changes"] += len(changes) if prev else 0
        if prev or is_new_worklog:
            title, body = _summary(text)
            detail = {
                "file": rel,
                "status_changes": [f"{t}: {s}" for t, s in changes][:30],
                "checked": new_checked[:20],
            }
            ev_title = (
                f"New worklog: {title}"
                if is_new_worklog
                else f"Updated {Path(rel).name}"
                + (f": {len(changes)} status change(s)" if changes else "")
            )
            ref = f"{rel}@{digest[:12]}"
            already = (
                db.query(CodeEvent.id)
                .filter(
                    CodeEvent.connection_id == conn.id,
                    CodeEvent.kind == "progress_file",
                    CodeEvent.ref == ref,
                )
                .first()
            )
            if not already:  # the same file content is recorded once, even after a re-baseline
                db.add(
                    CodeEvent(
                        connection_id=conn.id,
                        project_id=conn.project_id,
                        kind="progress_file",
                        ref=ref,
                        title=privacy.clean(db, ev_title, 300),
                        summary=privacy.clean(db, body, 800) if is_new_worklog else None,
                        detail=detail,
                        occurred_at=now(),
                    )
                )
                conn.last_activity_at = now()
        state[rel] = {"hash": digest, "ids": parsed["ids"], "checked": parsed["checked"][-300:]}
    conn.file_state = state
    return result
