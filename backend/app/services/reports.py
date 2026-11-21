"""Deterministic report generation from stored data (Markdown output, editable afterwards).

Principles: never invent progress — every line is derived from a stored record; empty
sections say "None recorded."; planned work is labelled separately from completed work."""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Milestone, Project, Task, TaskActivity, WorkLog
from app.models.enums import ProjectStatus, ReportKind, TaskStatus, WorkLogKind
from app.schemas.planning import ReportDraft
from app.services.progress import weighted_progress
from app.services.tasks import DONE

NONE = "_None recorded._"
PRIORITY_LABEL = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
STATUS_LABEL = {
    "todo": "To Do",
    "in_progress": "In Progress",
    "blocked": "Blocked",
    "in_review": "In Review",
    "completed": "Completed",
    "cancelled": "Cancelled",
}


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    tz = datetime.now().astimezone().tzinfo
    return (
        datetime.combine(start, time.min, tzinfo=tz),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
    )


def _fmt(d: date) -> str:
    return d.strftime("%A %d %B %Y").replace(" 0", " ")


def _short(d: date | None) -> str:
    return d.strftime("%d %b").lstrip("0") if d else "—"


class _Ctx:
    def __init__(self, db: Session, start: date, end: date, project_id, technical: bool):
        self.db, self.start, self.end, self.project_id = db, start, end, project_id
        self.technical = technical
        self.lo, self.hi = _bounds(start, end)

    def scope(self, stmt, col):
        if self.project_id:
            return stmt.where(col == self.project_id)
        return stmt

    def live(self):
        stmt = (
            select(Task)
            .join(Project, Project.id == Task.project_id)
            .where(Task.archived_at.is_(None), Project.status != ProjectStatus.ARCHIVED)
        )
        return self.scope(stmt, Task.project_id)

    def task_line(self, t: Task, extra: str = "") -> str:
        parts = [f"**{t.title}**"]
        if not self.project_id:
            parts.append(f"({t.project.name})")
        if self.technical:
            meta = [STATUS_LABEL[t.status.value], PRIORITY_LABEL[t.priority.value]]
            if t.workstream:
                meta.append(t.workstream.name)
            if t.estimate_hours is not None:
                meta.append(f"est. {t.estimate_hours:g}h")
            if t.actual_hours is not None:
                meta.append(f"actual {t.actual_hours:g}h")
            parts.append("— " + ", ".join(meta))
        if extra:
            parts.append(extra)
        return "- " + " ".join(parts)

    def completed(self) -> list[Task]:
        return list(
            self.db.scalars(
                self.live()
                .where(Task.completed_at >= self.lo, Task.completed_at < self.hi)
                .order_by(Task.completed_at)
            ).unique()
        )

    def logs(self, kinds: set[WorkLogKind] | None = None) -> list[WorkLog]:
        stmt = select(WorkLog).where(
            WorkLog.entry_date >= self.start, WorkLog.entry_date <= self.end
        )
        stmt = self.scope(stmt, WorkLog.project_id).order_by(WorkLog.entry_date, WorkLog.created_at)
        logs = list(self.db.scalars(stmt).unique())
        return [w for w in logs if kinds is None or w.kind in kinds]

    def log_lines(self, logs: list[WorkLog], with_date: bool) -> list[str]:
        out = []
        for w in logs:
            prefix = f"{_short(w.entry_date)}: " if with_date else ""
            ctx = []
            if w.project and not self.project_id:
                ctx.append(w.project.name)
            if w.task:
                ctx.append(f"task “{w.task.title}”")
            suffix = f" _({'; '.join(ctx)})_" if ctx else ""
            hours = f" [{w.hours:g}h]" if self.technical and w.hours else ""
            out.append(f"- {prefix}{w.summary.strip()}{suffix}{hours}")
        return out

    def updated_tasks(self, exclude: set[uuid.UUID]) -> list[tuple[Task, list[str]]]:
        stmt = select(TaskActivity).where(
            TaskActivity.created_at >= self.lo, TaskActivity.created_at < self.hi
        )
        stmt = self.scope(stmt, TaskActivity.project_id).order_by(TaskActivity.created_at)
        changes: dict[uuid.UUID, list[str]] = defaultdict(list)
        for a in self.db.scalars(stmt):
            if a.task_id in exclude:
                continue
            c = a.changes or {}
            if "status" in c:
                changes[a.task_id].append(
                    f"status {STATUS_LABEL.get(c['status'][0], c['status'][0])} → "
                    f"{STATUS_LABEL.get(c['status'][1], c['status'][1])}"
                )
            if "progress" in c:
                changes[a.task_id].append(f"progress {c['progress'][0]}% → {c['progress'][1]}%")
            if a.action == "created":
                changes[a.task_id].append("created")
            if a.action == "commented":
                changes[a.task_id].append("comment added")
        out = []
        for tid, ch in changes.items():
            t = self.db.get(Task, tid)
            if t and t.archived_at is None:
                out.append((t, list(dict.fromkeys(ch))))
        return out

    def blocked(self) -> list[Task]:
        return list(self.db.scalars(self.live().where(Task.status == TaskStatus.BLOCKED)).unique())


def _section(title: str, lines: list[str]) -> str:
    return f"## {title}\n\n" + ("\n".join(lines) if lines else NONE) + "\n"


def _title(kind: str, ctx: _Ctx, project: Project | None) -> str:
    scope = f" — {project.name}" if project else ""
    if kind == "daily":
        return f"Daily report{scope}: {_fmt(ctx.start)}"
    if kind == "weekly":
        return f"Weekly report{scope}: w/c {_fmt(ctx.start)}"
    return f"Project report{scope}: {_fmt(ctx.end)}"


def daily(ctx: _Ctx) -> list[str]:
    done = ctx.completed()
    updated = ctx.updated_tasks({t.id for t in done})
    logs = ctx.logs()
    tomorrow = ctx.end + timedelta(days=1)
    next_steps = list(
        ctx.db.scalars(
            ctx.live()
            .where(Task.scheduled_date == tomorrow, Task.status.not_in(DONE))
            .order_by(Task.position)
        ).unique()
    )
    return [
        _section("Work completed", [ctx.task_line(t) for t in done]),
        _section(
            "Tasks updated", [ctx.task_line(t, f"— {', '.join(ch)}") for t, ch in updated if ch]
        ),
        _section(
            "Progress updates",
            ctx.log_lines(
                [w for w in logs if w.kind in {WorkLogKind.PROGRESS, WorkLogKind.NOTE}], False
            ),
        ),
        _section(
            "Unplanned work",
            ctx.log_lines([w for w in logs if w.kind == WorkLogKind.UNPLANNED], False),
        ),
        _section(
            "Decisions", ctx.log_lines([w for w in logs if w.kind == WorkLogKind.DECISION], False)
        ),
        _section(
            "Blockers",
            ctx.log_lines([w for w in logs if w.kind == WorkLogKind.BLOCKER], False)
            + [ctx.task_line(t, "— currently Blocked") for t in ctx.blocked()],
        ),
        _section(
            "Research conducted",
            ctx.log_lines([w for w in logs if w.kind == WorkLogKind.RESEARCH], False),
        ),
        _section(
            f"Next steps (planned for {_fmt(tomorrow)})", [ctx.task_line(t) for t in next_steps]
        ),
    ]


def weekly(ctx: _Ctx) -> list[str]:
    done = ctx.completed()
    done_ids = {t.id for t in done}
    planned = list(
        ctx.db.scalars(
            ctx.live().where(Task.scheduled_date >= ctx.start, Task.scheduled_date <= ctx.end)
        ).unique()
    )
    outstanding = [t for t in planned if t.status not in DONE]
    planned_done = [t for t in planned if t.id in done_ids]
    unplanned_done = [t for t in done if t.id not in {p.id for p in planned}]
    logs = ctx.logs()
    hours_logged = sum(float(w.hours or 0) for w in logs)

    ms_stmt = select(Milestone).join(Project).where(Project.status != ProjectStatus.ARCHIVED)
    ms_stmt = ctx.scope(ms_stmt, Milestone.project_id)
    milestone_lines = []
    touched_ms = {t.milestone_id for t in done} | {
        t.milestone_id for t, _ in ctx.updated_tasks(set())
    }
    for m in ctx.db.scalars(ms_stmt.order_by(Milestone.due_date.asc().nulls_last())):
        achieved = m.achieved_at and ctx.lo <= m.achieved_at < ctx.hi
        if m.id not in touched_ms and not achieved:
            continue
        mtasks = list(
            ctx.db.scalars(
                select(Task).where(
                    Task.milestone_id == m.id, Task.archived_at.is_(None), Task.parent_id.is_(None)
                )
            )
        )
        p = weighted_progress(mtasks)
        label = " — **achieved this week**" if achieved else ""
        milestone_lines.append(
            f"- **{m.title}**{'' if ctx.project_id else f' ({m.project.name})'}: "
            f"{p.percent:.0f}% complete, due {_short(m.due_date)}{label}"
        )
    nw_start, nw_end = ctx.end + timedelta(days=1), ctx.end + timedelta(days=7)
    upcoming = list(
        ctx.db.scalars(
            ctx.live()
            .where(
                Task.status.not_in(DONE),
                ((Task.scheduled_date >= nw_start) & (Task.scheduled_date <= nw_end))
                | ((Task.due_date >= nw_start) & (Task.due_date <= nw_end)),
            )
            .order_by(Task.due_date.asc().nulls_last())
        ).unique()
    )
    overdue = list(
        ctx.db.scalars(
            ctx.live().where(
                Task.status.not_in(DONE), Task.due_date <= ctx.end, Task.due_date.is_not(None)
            )
        ).unique()
    )
    pva = [
        f"- Tasks planned this week: **{len(planned)}**",
        f"- Planned tasks completed: **{len(planned_done)}**"
        + (f" ({len(planned_done) / len(planned) * 100:.0f}%)" if planned else ""),
        f"- Unplanned tasks completed: **{len(unplanned_done)}**",
        f"- Planned tasks outstanding: **{len(outstanding)}**",
    ]
    if ctx.technical:
        est = sum(float(t.estimate_hours or 0) for t in planned)
        pva.append(f"- Estimated effort planned: **{est:g}h**; hours logged: **{hours_logged:g}h**")
    return [
        _section("Achievements (tasks completed)", [ctx.task_line(t) for t in done]),
        _section("Milestones progressed", milestone_lines),
        _section("Planned versus actual", pva),
        _section(
            "Tasks outstanding (planned this week, not completed)",
            [ctx.task_line(t, f"— {t.progress}%") for t in outstanding],
        ),
        _section(
            "Blockers",
            ctx.log_lines([w for w in logs if w.kind == WorkLogKind.BLOCKER], True)
            + [ctx.task_line(t, "— currently Blocked") for t in ctx.blocked()],
        ),
        _section(
            "Risks", [ctx.task_line(t, f"— overdue (due {_short(t.due_date)})") for t in overdue]
        ),
        _section(
            "Decisions", ctx.log_lines([w for w in logs if w.kind == WorkLogKind.DECISION], True)
        ),
        _section(
            "Research", ctx.log_lines([w for w in logs if w.kind == WorkLogKind.RESEARCH], True)
        ),
        _section(
            "Upcoming priorities (planned for next week — not yet done)",
            [
                ctx.task_line(t, f"— due {_short(t.due_date)}" if t.due_date else "")
                for t in upcoming
            ],
        ),
    ]


def project_report(ctx: _Ctx, project: Project) -> list[str]:
    tasks = list(
        ctx.db.scalars(
            select(Task).where(Task.project_id == project.id, Task.archived_at.is_(None))
        )
    )
    top = [t for t in tasks if t.parent_id is None]
    p = weighted_progress(top)
    counts = defaultdict(int)
    for t in tasks:
        counts[t.status.value] += 1
    overview = [
        f"- Status: **{project.status.value.replace('_', ' ').title()}**"
        + (f"; stage: **{project.stage.name}**" if project.stage else ""),
        f"- Overall progress: **{p.percent:.0f}%** — {p.explanation}",
        f"- Target completion: {_fmt(project.target_date) if project.target_date else 'not set'}",
        "- Tasks: " + (", ".join(f"{STATUS_LABEL[k]} {v}" for k, v in counts.items()) or "none"),
    ]
    ms_lines, deliverables = [], []
    for m in project.milestones:
        mp = weighted_progress([t for t in top if t.milestone_id == m.id])
        ms_lines.append(
            f"- **{m.title}** — {m.status.value.replace('_', ' ')}, "
            f"{mp.percent:.0f}%, due {_short(m.due_date)}"
        )
        if (m.deliverables or "").strip():
            deliverables.append(f"- **{m.title}**: {m.deliverables.strip()}")
    outstanding = [t for t in top if t.status not in DONE]
    outstanding.sort(key=lambda t: t.due_date or date.max)
    logs = ctx.logs()
    return [
        _section("Overall progress", overview),
        _section("Objectives", [project.objectives.strip()] if project.objectives else []),
        _section("Milestones", ms_lines),
        _section("Deliverables", deliverables),
        _section(
            f"Outstanding work ({len(outstanding)} task(s))",
            [
                ctx.task_line(t, f"— {t.progress}%, due {_short(t.due_date)}")
                for t in outstanding[:40]
            ],
        ),
        _section(
            "Risks and assumptions",
            [project.risks_assumptions.strip()] if project.risks_assumptions else [],
        ),
        _section(
            "Decisions", ctx.log_lines([w for w in logs if w.kind == WorkLogKind.DECISION], True)
        ),
        _section("Blockers", [ctx.task_line(t) for t in tasks if t.status == TaskStatus.BLOCKED]),
    ]


def generate(db: Session, kind: ReportKind, day: date, project_id, audience: str) -> ReportDraft:
    project = db.get(Project, project_id) if project_id else None
    technical = audience == "technical"
    if kind == ReportKind.DAILY:
        start = end = day
    elif kind == ReportKind.WEEKLY:
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=6)
    else:
        if not project:
            raise ValueError("A project report needs a project.")
        start, end = project.start_date or project.created_at.date(), day
    ctx = _Ctx(db, start, end, project_id, technical)
    if kind == ReportKind.DAILY:
        sections = daily(ctx)
    elif kind == ReportKind.WEEKLY:
        sections = weekly(ctx)
    else:
        sections = project_report(ctx, project)
    title = _title(kind.value, ctx, project)
    generated = datetime.now().astimezone()
    footer = (
        f"\n---\n_Generated from workspace data on {generated:%d %B %Y at %H:%M}. "
        f"{'Technical' if technical else 'Stakeholder'} format. Edit before sharing._\n"
    )
    content = f"# {title}\n\n" + "\n".join(sections) + footer
    return ReportDraft(
        kind=kind,
        title=title,
        period_start=start,
        period_end=end,
        project_id=project_id,
        content=content,
        generated_at=generated,
    )
