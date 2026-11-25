"""Turn a project tracker into suggestions for review (ADR 0010).

Each refresh reads the newest tracker, matches every item to an existing task or milestone and
proposes only what is new or whose status moved forward. Nothing changes until the suggestion is
approved (ADR 0002). `TrackerEntry` remembers what has been proposed, so rejected items are not
proposed again unless the tracker changes their status."""

import re
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Milestone, ProjectConnection, Suggestion, Task, TrackerEntry
from app.models.enums import MilestoneStatus
from app.models.voice import SuggestionKind, SuggestionStatus
from app.services import files, privacy, text_tools, tracker
from app.services.tasks import now

GENERATOR = "tracker"
# Forward order of task statuses: a tracker never proposes moving a task backwards.
RANK = {"todo": 0, "blocked": 1, "in_progress": 1, "in_review": 2, "completed": 3, "cancelled": 3}
STOP = {
    "a", "an", "and", "the", "of", "in", "on", "for", "to", "with", "by", "at", "from", "as",
    "is", "are", "be", "or", "its", "it", "into", "via", "all", "per", "new",
}  # fmt: skip
CODE_RE = re.compile(r"\bM(\d{1,3})\b")
NO_TRACKER = (
    "No tracker found. Keep one at docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md "
    "(Administration → Projects folder has instructions for Claude Code)."
)


# ---------------------------------------------------------------- matching
def _words(text: str) -> set[str]:
    return {w for w in text_tools.normalise_title(text).split() if w not in STOP and len(w) > 1}


def overlap(a: str, b: str) -> float:
    """Share of the shorter title's key words found in the other (0 when under 3 key words)."""
    wa, wb = _words(a), _words(b)
    small = min(len(wa), len(wb))
    return len(wa & wb) / small if small >= 3 else 0.0


def same_work(a: str, b: str) -> bool:
    """Near-identical titles, or one title's key words almost all contained in the other."""
    return text_tools.similar(a, b) or overlap(a, b) >= 0.8


# "ISSUE-0032 logged" records a new issue: it is not progress on that issue.
LOGGED_RE = re.compile(r"(?i)\b(logged|opened|raised|found|filed|identified|reported|created)\b")
DUPLICATE_HINT = 0.6


def match_task(tasks: list[Task], item: tracker.TrackerItem) -> Task | None:
    """The same piece of work: a task ID the item works on, or a near-identical title.
    Looser matches are only offered as a possible duplicate (see `likely_duplicate`)."""
    if item.task_ids and not LOGGED_RE.search(item.title):
        ids = set(item.task_ids)
        for t in tasks:
            if ids & set(tracker.ID_RE.findall(t.title)):
                return t
    return next((t for t in tasks if text_tools.similar(t.title, item.title)), None)


def likely_duplicate(tasks: list[Task], title: str) -> Task | None:
    best, score = None, 0.0
    for t in tasks:
        sc = 1.0 if text_tools.similar(t.title, title) else overlap(t.title, title)
        if sc > score:
            best, score = t, sc
    return best if score >= DUPLICATE_HINT else None


def match_milestone(milestones: list[Milestone], ms: tracker.TrackerMilestone) -> Milestone | None:
    if ms.code:
        num = ms.code[1:]
        for m in milestones:
            if any(n == num for n in CODE_RE.findall(m.title)):
                return m
    return next((m for m in milestones if same_work(m.title, ms.title)), None)


def _is_forward(current: str, proposed: str) -> bool:
    if current == proposed:
        return False
    if proposed == "blocked":
        return current not in ("completed", "cancelled")
    return RANK.get(proposed, 0) > RANK.get(current, 0)


def _pending_update(db: Session, task_id: uuid.UUID, status: str) -> bool:
    """A pending suggestion (from any source) already proposes this status for the task."""
    return bool(
        db.scalar(
            select(Suggestion.id).where(
                Suggestion.kind == SuggestionKind.TASK_UPDATE,
                Suggestion.status == SuggestionStatus.PENDING,
                Suggestion.payload["task_id"].astext == str(task_id),
                Suggestion.payload["status"].astext == status,
            )
        )
    )


# ---------------------------------------------------------------- refresh
def refresh_tracker(db: Session, conn: ProjectConnection) -> dict:
    """Read the connection's tracker and create pending suggestions. Commits."""
    result = {
        "file": None,
        "milestones": 0,
        "tasks": 0,
        "updates": 0,
        "work_logs": 0,
        "already_reflected": 0,
        "warnings": [],
    }
    try:
        read = tracker.read_tracker(conn.path)
    except (files.PathError, OSError) as e:
        read, result["warnings"] = None, [str(e)]
    conn.tracker_read_at = now()
    if not read:
        conn.tracker_file = None
        conn.tracker_warnings = result["warnings"] or [NO_TRACKER]
        result["warnings"] = conn.tracker_warnings
        db.commit()
        return result
    rel, file_date, text = read
    parsed = tracker.parse_tracker(text, file_date)
    pid = conn.project_id
    result["file"] = rel

    entries = {
        e.key: e for e in db.scalars(select(TrackerEntry).where(TrackerEntry.project_id == pid))
    }
    tasks = list(db.scalars(select(Task).where(Task.project_id == pid, Task.archived_at.is_(None))))
    milestones = list(db.scalars(select(Milestone).where(Milestone.project_id == pid)))
    clean = lambda t, n=300: privacy.clean(db, t, n)  # noqa: E731

    def entry_for(key, kind, title, status, item_date=None) -> TrackerEntry:
        e = entries.get(key)
        if not e:
            e = TrackerEntry(project_id=pid, key=key, kind=kind, title=(title or "")[:300])
            db.add(e)
            entries[key] = e
        e.status, e.item_date = status, item_date
        return e

    def suggest(kind, payload, evidence) -> Suggestion:
        s = Suggestion(
            kind=kind,
            source_type="tracker",
            source_id=None,
            project_id=pid,
            generator=GENERATOR,
            payload={**payload, "tracker_file": rel},
            evidence=clean(evidence, 2000),
        )
        db.add(s)
        db.flush()
        return s

    # Milestones first, so tasks can name the milestone they belong to.
    ms_info: dict[str, dict] = {}
    for m in parsed.milestones:
        e = entries.get(m.key)
        existing = (db.get(Milestone, e.milestone_id) if e and e.milestone_id else None) or (
            match_milestone(milestones, m)
        )
        ms_info[m.key] = {"id": str(existing.id) if existing else None, "title": m.title}
        if e and e.status == m.status:
            continue
        if (
            existing
            and existing.status.value == m.status
            and (not m.due_date or existing.due_date == m.due_date)
        ):
            entry_for(m.key, "milestone", m.title, m.status, m.due_date).milestone_id = existing.id
            result["already_reflected"] += 1
            continue
        if existing and RANK.get(m.status, 0) < RANK.get(existing.status.value, 0):
            continue  # never propose moving a milestone backwards
        s = suggest(
            SuggestionKind.MILESTONE,
            {
                "title": clean(m.title, 200),
                "code": m.code,
                "due_date": m.due_date.isoformat() if m.due_date else None,
                "status": m.status,
                "description": clean(m.description, 2000),
                "milestone_id": str(existing.id) if existing else None,
                "tracker_key": m.key,
                "section": m.section,
            },
            f"{rel} · {m.section}: {m.title}",
        )
        e = entry_for(m.key, "milestone", m.title, m.status, m.due_date)
        e.suggestion_id, e.milestone_id = s.id, existing.id if existing else None
        result["milestones"] += 1

    for it in parsed.items:
        e = entries.get(it.key)
        if e and e.status == it.status:
            continue
        task = (db.get(Task, e.task_id) if e and e.task_id else None) or match_task(tasks, it)
        ms = ms_info.get(it.milestone_key or "", {})
        base = {
            "tracker_key": it.key,
            "tracker_kind": it.kind,
            "item_date": it.item_date.isoformat() if it.item_date else None,
            "original_date": it.original_date.isoformat() if it.original_date else None,
            "milestone_key": it.milestone_key,
            "milestone_id": ms.get("id"),
            "milestone_title": ms.get("title"),
            "section": it.section,
        }
        evidence = f"{rel} · {it.section}: {it.evidence or it.title}"
        # Planned work on an open task: propose its day and milestone, even without a status change.
        schedules = False
        if task and it.kind == "plan" and task.status.value not in ("completed", "cancelled"):
            needs_day = bool(it.item_date) and task.scheduled_date != it.item_date  # or reschedule
            needs_ms = bool(ms.get("id") or it.milestone_key) and task.milestone_id is None
            schedules = needs_day or needs_ms
        if task:
            if not schedules and (
                task.archived_at
                or not _is_forward(task.status.value, it.status)
                or (_pending_update(db, task.id, it.status))
            ):
                ent = entry_for(it.key, it.kind, it.title, it.status, it.item_date)
                ent.task_id = task.id
                result["already_reflected"] += 1
                continue
            s = suggest(
                SuggestionKind.TASK_UPDATE,
                {
                    **base,
                    "task_id": str(task.id),
                    "title": task.title,
                    "tracker_title": clean(it.title),
                    "status": it.status
                    if _is_forward(task.status.value, it.status)
                    else task.status.value,
                    "current_status": task.status.value,
                    "task_has_milestone": task.milestone_id is not None,  # approval keeps it
                    "scheduled_date": base["item_date"] if schedules else None,
                    "current_scheduled_date": task.scheduled_date.isoformat()
                    if task.scheduled_date
                    else None,
                },
                evidence,
            )
            result["updates"] += 1
        else:
            dup = likely_duplicate(tasks, it.title)
            s = suggest(
                SuggestionKind.TASK,
                {
                    **base,
                    "title": clean(it.title),
                    "status": it.status,
                    "priority": "medium",
                    "scheduled_date": base["item_date"] if it.kind == "plan" else None,
                    "acceptance_criteria": clean(it.acceptance_criteria, 2000),
                },
                evidence,
            )
            if dup:
                s.duplicate_of_task_id = dup.id  # shown as "possibly the same as…"; not blocking
            result["tasks"] += 1
        ent = entry_for(it.key, it.kind, it.title, it.status, it.item_date)
        ent.suggestion_id = s.id
        ent.task_id = task.id if task else ent.task_id

    for d in parsed.days:
        if d.key in entries:
            continue
        carried = ", ".join(x.strftime("%a %-d %b") for x in d.original_dates)
        s = suggest(
            SuggestionKind.PROGRESS,
            {
                "tracker_key": d.key,
                "tracker_kind": "day",
                "title": f"Work done on {d.item_date:%a %-d %b %Y}",
                "entry_date": d.item_date.isoformat(),
                "item_date": d.item_date.isoformat(),
                "carried_from": carried or None,
                "section": d.section,
            },
            (f"Includes weekend work from {carried}. " if carried else "") + d.text,
        )
        entry_for(
            d.key, "day", f"Work done {d.item_date}", "logged", d.item_date
        ).suggestion_id = s.id
        result["work_logs"] += 1

    conn.tracker_file = rel
    conn.tracker_warnings = parsed.warnings
    result["warnings"] = parsed.warnings
    db.commit()
    return result


# ---------------------------------------------------------------- approval hooks
def resolve_milestone(db: Session, project_id: uuid.UUID, payload: dict) -> uuid.UUID | None:
    """The milestone a tracker task belongs to: the matched one, or the one created when its
    milestone suggestion was approved."""
    if payload.get("milestone_id"):
        m = db.get(Milestone, uuid.UUID(payload["milestone_id"]))
        if m and m.project_id == project_id:
            return m.id
    key = payload.get("milestone_key")
    if key:
        e = db.scalar(
            select(TrackerEntry).where(
                TrackerEntry.project_id == project_id, TrackerEntry.key == key
            )
        )
        if e and e.milestone_id:
            return e.milestone_id
    return None


def record_approval(db: Session, s: Suggestion, task_id=None, milestone_id=None) -> None:
    key = (s.payload or {}).get("tracker_key")
    if not key or not s.project_id:
        return
    e = db.scalar(
        select(TrackerEntry).where(TrackerEntry.project_id == s.project_id, TrackerEntry.key == key)
    )
    if e:
        e.task_id = task_id or e.task_id
        e.milestone_id = milestone_id or e.milestone_id


def apply_milestone(db: Session, s: Suggestion, edits: dict) -> Milestone:
    """Create the milestone, or update the matched one (status, due date, description)."""
    p = {**s.payload, **{k: v for k, v in edits.items() if v is not None}}
    status = MilestoneStatus(p.get("status") or "planned")
    due = p.get("due_date")
    due = date.fromisoformat(due) if isinstance(due, str) else due
    m = None
    if p.get("milestone_id"):
        m = db.get(Milestone, uuid.UUID(str(p["milestone_id"])))
        if m and m.project_id != s.project_id:
            m = None
    if m is None:
        m = Milestone(project_id=s.project_id, title=(p.get("title") or "Milestone")[:200])
        db.add(m)
    else:
        m.title = (edits.get("title") or m.title)[:200]
    m.due_date = due or m.due_date
    if p.get("description") and not m.description:
        m.description = p["description"]
    if status == MilestoneStatus.ACHIEVED and m.status != MilestoneStatus.ACHIEVED:
        m.achieved_at = now()
    m.status = status
    db.flush()
    record_approval(db, s, milestone_id=m.id)
    return m


def pending_count(db: Session, project_id: uuid.UUID) -> int:
    return len(
        list(
            db.scalars(
                select(Suggestion.id).where(
                    Suggestion.project_id == project_id,
                    Suggestion.generator == GENERATOR,
                    Suggestion.status == SuggestionStatus.PENDING,
                )
            )
        )
    )
