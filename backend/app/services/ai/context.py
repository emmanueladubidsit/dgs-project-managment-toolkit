"""Builds grounded, size-limited context from workspace data, with a list of the sources used."""

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import KnowledgeItem, KnowledgeProjectLink, Project, Task, WorkLog
from app.models.enums import MilestoneStatus, ProjectStatus
from app.services import privacy
from app.services.progress import weighted_progress
from app.services.tasks import DONE


@dataclass
class Context:
    text: str = ""
    sources: list[dict] = field(default_factory=list)

    def add(self, kind: str, id_: uuid.UUID, title: str) -> None:
        self.sources.append({"type": kind, "id": str(id_), "title": title})


def _clip(s: str | None, n: int = 400) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s[:n] + ("…" if len(s) > n else "")


def project_context(db: Session, project_id: uuid.UUID, limit_chars: int = 16000) -> Context:
    p = db.get(Project, project_id)
    ctx = Context()
    if not p:
        return ctx
    ctx.add("project", p.id, p.name)
    tasks = list(
        db.scalars(select(Task).where(Task.project_id == p.id, Task.archived_at.is_(None)))
    )
    top = [t for t in tasks if t.parent_id is None]
    prog = weighted_progress(top)
    lines = [
        f"# Project: {p.name}",
        f"Status: {p.status.value}; stage: {p.stage.name if p.stage else 'not set'}; "
        f"priority: {p.priority.value}; start: {p.start_date or 'not set'}; "
        f"target: {p.target_date or 'not set'}; today: {date.today()}",
        f"Progress: {prog.percent:.0f}% ({prog.explanation})",
    ]
    for label, value in [
        ("Description", p.description),
        ("Problem", p.problem_statement),
        ("Objectives", p.objectives),
        ("Target users", p.target_users),
        ("Scope", p.scope),
        ("Out of scope", p.out_of_scope),
        ("Expected outcomes", p.expected_outcomes),
        ("Stakeholders", p.stakeholders),
        ("Risks and assumptions", p.risks_assumptions),
        ("Technology", p.tech_stack),
    ]:
        if value:
            lines.append(f"{label}: {_clip(value, 800)}")
    ms = sorted(p.milestones, key=lambda m: (m.due_date is None, m.due_date))
    if ms:
        lines.append("\n## Milestones")
        for m in ms:
            mp = weighted_progress([t for t in top if t.milestone_id == m.id])
            lines.append(
                f"- {m.title} — {m.status.value}, due {m.due_date or 'not set'}, "
                f"{mp.percent:.0f}%; deliverables: {_clip(m.deliverables, 200) or 'none'}"
            )
            ctx.add("milestone", m.id, m.title)
    open_tasks = sorted(
        [t for t in tasks if t.status not in DONE], key=lambda t: (t.due_date is None, t.due_date)
    )[:40]
    if open_tasks:
        lines.append("\n## Open tasks")
        for t in open_tasks:
            lines.append(
                f"- {t.title} [{t.status.value}, {t.priority.value}, {t.progress}%"
                f"{', due ' + str(t.due_date) if t.due_date else ''}]"
            )
            ctx.add("task", t.id, t.title)
    done = sorted([t for t in tasks if t.completed_at], key=lambda t: t.completed_at, reverse=True)[
        :15
    ]
    if done:
        lines.append("\n## Recently completed")
        lines += [f"- {t.title} (completed {t.completed_at.date()})" for t in done]
    since = date.today() - timedelta(days=30)
    logs = db.scalars(
        select(WorkLog)
        .where(WorkLog.project_id == p.id, WorkLog.entry_date >= since)
        .order_by(WorkLog.entry_date.desc())
        .limit(25)
    ).unique()
    logs = list(logs)
    if logs:
        lines.append("\n## Recent updates, decisions and blockers (last 30 days)")
        lines += [f"- {w.entry_date} {w.kind.value}: {_clip(w.summary, 300)}" for w in logs]
    k_ids = select(KnowledgeProjectLink.item_id).where(KnowledgeProjectLink.project_id == p.id)
    knowledge = list(
        db.scalars(
            select(KnowledgeItem)
            .where(KnowledgeItem.id.in_(k_ids), KnowledgeItem.archived_at.is_(None))
            .limit(15)
        )
    )
    if knowledge:
        lines.append("\n## Linked knowledge")
        for k in knowledge:
            body = k.summary or " ".join(k.fields.values()) or k.content
            lines.append(
                f"- {k.title} ({k.category.value}, {k.verification.value}): {_clip(body, 300)}"
            )
            ctx.add("knowledge", k.id, k.title)
    ctx.text = privacy.clean(db, "\n".join(lines))[:limit_chars]
    return ctx


def workspace_context(db: Session, limit_chars: int = 16000) -> Context:
    """Portfolio overview across active projects."""
    ctx = Context()
    lines = [f"# Workspace overview (today: {date.today()})"]
    projects = db.scalars(select(Project).where(Project.status == ProjectStatus.ACTIVE)).unique()
    for p in projects:
        tasks = list(
            db.scalars(select(Task).where(Task.project_id == p.id, Task.archived_at.is_(None)))
        )
        top = [t for t in tasks if t.parent_id is None]
        overdue = [
            t for t in tasks if t.due_date and t.due_date < date.today() and t.status not in DONE
        ]
        blocked = [t for t in tasks if t.status.value == "blocked"]
        nxt = [
            m
            for m in sorted(p.milestones, key=lambda m: (m.due_date is None, m.due_date))
            if m.status in (MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS)
        ][:1]
        lines.append(
            f"\n## {p.name}: {weighted_progress(top).percent:.0f}% complete, "
            f"{len([t for t in tasks if t.status not in DONE])} open tasks, "
            f"{len(overdue)} overdue, {len(blocked)} blocked"
            + (f"; next milestone {nxt[0].title} due {nxt[0].due_date}" if nxt else "")
        )
        lines += [f"- Overdue: {t.title} (due {t.due_date})" for t in overdue[:5]]
        lines += [f"- Blocked: {t.title}" for t in blocked[:5]]
        ctx.add("project", p.id, p.name)
    ctx.text = privacy.clean(db, "\n".join(lines))[:limit_chars]
    return ctx


def knowledge_search_context(db: Session, query: str, limit: int = 8) -> Context:
    """Relevant knowledge items by simple keyword match (for questions and research)."""
    ctx = Context()
    words = [w for w in query.lower().split() if len(w) > 3][:8]
    if not words:
        return ctx
    conds = [KnowledgeItem.title.ilike(f"%{w}%") for w in words] + [
        KnowledgeItem.summary.ilike(f"%{w}%") for w in words
    ]
    items = db.scalars(
        select(KnowledgeItem).where(KnowledgeItem.archived_at.is_(None), or_(*conds)).limit(limit)
    ).all()
    if items:
        lines = ["\n## Possibly relevant knowledge from the library"]
        for k in items:
            body = k.summary or " ".join(k.fields.values()) or k.content
            lines.append(
                f"- {k.title} ({k.category.value}, verification: {k.verification.value}): "
                f"{_clip(body, 500)}"
            )
            ctx.add("knowledge", k.id, k.title)
        ctx.text = privacy.clean(db, "\n".join(lines))
    return ctx
