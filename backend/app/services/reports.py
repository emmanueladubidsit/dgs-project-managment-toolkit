"""Deterministic report generation from stored data (Markdown output, editable afterwards).

Principles: never invent progress — every line is derived from a stored record; empty sections
are left out and named once in a closing note ("No decisions or research recorded…"); planned
work is labelled separately from completed work. Portfolio reports group lines under a heading per
project instead of repeating the project name; weekend work counts on the following Monday."""

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
from app.services.tracker import working_day

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

    @property
    def portfolio(self) -> bool:
        return not self.project_id

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

    def task_line(self, t: Task, extra: str = "", day: date | None = None) -> str:
        """One plain line per task; the project is shown by the group heading, not repeated."""
        text = f"{_day(day)}: {t.title}" if day else t.title
        if extra:
            text += f" — {extra}"
        if self.technical:
            meta = [STATUS_LABEL[t.status.value], PRIORITY_LABEL[t.priority.value]]
            if t.workstream:
                meta.append(t.workstream.name)
            if t.estimate_hours is not None:
                meta.append(f"est. {t.estimate_hours:g}h")
            if t.actual_hours is not None:
                meta.append(f"actual {t.actual_hours:g}h")
            text += f" _({' · '.join(meta)})_"
        return f"- {text}"

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

    def log_items(self, logs: list[WorkLog], with_date: bool) -> list[tuple[str, str]]:
        """(group, line) pairs for work-log entries. Long entries keep only their first line."""
        out = []
        for w in logs:
            first, *rest = [ln.strip() for ln in w.summary.strip().splitlines() if ln.strip()] or [
                ""
            ]
            text = first + (" …" if rest and not self.technical else "")
            if self.technical and rest:
                text += "\n" + "\n".join(f"  {ln}" for ln in rest[:12])
            prefix = f"{_day(w.entry_date)}: " if with_date else ""
            task = f" _(task “{w.task.title}”)_" if w.task else ""
            hours = f" [{w.hours:g}h]" if self.technical and w.hours else ""
            group = w.project.name if w.project else "General"
            out.append((group, f"- {prefix}{text}{task}{hours}"))
        return out

    def changes(self) -> tuple[dict[uuid.UUID, dict], dict[uuid.UUID, int]]:
        """Status/progress changes per task (first → last value) and tasks added, in the period."""
        stmt = select(TaskActivity).where(
            TaskActivity.created_at >= self.lo, TaskActivity.created_at < self.hi
        )
        stmt = self.scope(stmt, TaskActivity.project_id).order_by(TaskActivity.created_at)
        moved: dict[uuid.UUID, dict] = defaultdict(dict)
        created: set[uuid.UUID] = set()
        for a in self.db.scalars(stmt):
            c = a.changes or {}
            if a.action == "created":
                created.add(a.task_id)
            for field in ("status", "progress"):
                if field in c:
                    first = moved[a.task_id].get(field, [c[field][0]])[0]
                    moved[a.task_id][field] = [first, c[field][1]]
        return moved, {t: 1 for t in created}

    def blocked(self) -> list[Task]:
        return list(self.db.scalars(self.live().where(Task.status == TaskStatus.BLOCKED)).unique())


def _n(n: int, word: str, plural: str | None = None) -> str:
    """“1 task”, “3 tasks” (number in bold)."""
    return f"**{n}** {word if n == 1 else plural or word + 's'}"


def _day(d: date) -> str:
    return d.strftime("%a %d %b").replace(" 0", " ")


def _grouped(ctx: _Ctx, items: list[tuple[str, str]]) -> list[str]:
    """Lines under a `### Project` heading per project in portfolio reports."""
    if not items:
        return []
    if not ctx.portfolio:
        return [line for _, line in items]
    groups: dict[str, list[str]] = defaultdict(list)
    for group, line in items:
        groups[group].append(line)
    out = []
    for name in sorted(groups, key=lambda g: (g == "General", g.lower())):
        out += [f"### {name}", "", *groups[name], ""]
    return out[:-1]


def _tasks(ctx: _Ctx, tasks: list[Task], extra=lambda t: "", day=lambda t: None) -> list[str]:
    return _grouped(ctx, [(t.project.name, ctx.task_line(t, extra(t), day(t))) for t in tasks])


class _Doc:
    """Sections in order; empty ones are left out and named once in a closing note."""

    def __init__(self):
        self.parts: list[str] = []
        self.empty: list[str] = []

    def add(self, title: str, lines: list[str], *, note_if_empty: str | None = None):
        if lines:
            self.parts.append(f"## {title}\n\n" + "\n".join(lines) + "\n")
        elif note_if_empty:
            self.empty.append(note_if_empty)

    def render(self, period: str) -> list[str]:
        out = list(self.parts)
        if self.empty:
            names = self.empty
            joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]
            out.append(f"_No {joined} recorded {period}._\n")
        return out


def _change_text(ch: dict) -> str:
    parts = []
    if "status" in ch:
        a, b = ch["status"]
        parts.append(f"{STATUS_LABEL.get(a, a)} → {STATUS_LABEL.get(b, b)}")
    if "progress" in ch and ch["progress"][0] != ch["progress"][1]:
        parts.append(f"progress {ch['progress'][0]}% → {ch['progress'][1]}%")
    return ", ".join(parts)


def _added(ctx: _Ctx, created: dict[uuid.UUID, int], exclude: set[uuid.UUID]) -> list[str]:
    """New tasks added in the period (those already reported as completed are not repeated)."""
    tasks = [
        t
        for tid in created
        if tid not in exclude and (t := ctx.db.get(Task, tid)) and t.archived_at is None
    ]
    if not tasks:
        return []
    if ctx.technical:
        return _tasks(ctx, tasks)
    per: dict[str, int] = defaultdict(int)
    for t in tasks:
        per[t.project.name] += 1
    if not ctx.portfolio:
        return [f"- {_n(len(tasks), 'new task')} added to the plan."]
    return [f"- {name}: {_n(n, 'new task')} added to the plan." for name, n in sorted(per.items())]


def _next_working_day(d: date) -> date:
    n = d + timedelta(days=1)
    while n.weekday() >= 5:
        n += timedelta(days=1)
    return n


def _milestone_line(ctx: _Ctx, m: Milestone, suffix: str = "") -> tuple[str, str]:
    top = list(
        ctx.db.scalars(
            select(Task).where(
                Task.milestone_id == m.id, Task.archived_at.is_(None), Task.parent_id.is_(None)
            )
        )
    )
    p = weighted_progress(top)
    done = sum(1 for t in top if t.status == TaskStatus.COMPLETED)
    due = f", due {_day(m.due_date)}" if m.due_date else ""
    return (
        m.project.name,
        f"- {m.title} — {done} of {len(top)} {'task' if len(top) == 1 else 'tasks'} done "
        f"({p.percent:.0f}%){due}{suffix}",
    )


def _glance(lines: list[str]) -> list[str]:
    return [ln for ln in lines if ln]


def daily(ctx: _Ctx) -> list[str]:
    done = ctx.completed()
    done_ids = {t.id for t in done}
    moved, created = ctx.changes()
    changed = [
        (t, txt)
        for tid, ch in moved.items()
        if tid not in done_ids
        and (t := ctx.db.get(Task, tid))
        and t.archived_at is None
        and (txt := _change_text(ch))
    ]
    logs = ctx.logs()
    blocked = ctx.blocked()
    nxt = _next_working_day(ctx.end)
    next_steps = list(
        ctx.db.scalars(
            ctx.live()
            .where(Task.scheduled_date == nxt, Task.status.not_in(DONE))
            .order_by(Task.position)
        ).unique()
    )
    by_kind = lambda *k: [w for w in logs if w.kind in k]  # noqa: E731
    projects = {t.project.name for t in done}
    doc = _Doc()
    doc.add(
        "At a glance",
        _glance(
            [
                f"- {_n(len(done), 'task')} completed"
                + (f" across {_n(len(projects), 'project')}" if ctx.portfolio and projects else ""),
                f"- {_n(len(changed), 'other task')} moved forward" if changed else "",
                f"- {_n(len(logs), 'update')} recorded" if logs else "",
                f"- {_n(len(blocked), 'task')} blocked" if blocked else "",
                f"- {_n(len(next_steps), 'task')} planned for {_fmt(nxt)}" if next_steps else "",
            ]
        ),
    )
    doc.add("Work completed", _tasks(ctx, done), note_if_empty="completed work")
    doc.add(
        "Progress on other tasks",
        _grouped(ctx, [(t.project.name, ctx.task_line(t, txt)) for t, txt in changed]),
    )
    doc.add("Added to the plan", _added(ctx, created, done_ids))
    doc.add(
        "Progress updates",
        _grouped(ctx, ctx.log_items(by_kind(WorkLogKind.PROGRESS, WorkLogKind.NOTE), False)),
        note_if_empty="progress updates",
    )
    doc.add("Unplanned work", _grouped(ctx, ctx.log_items(by_kind(WorkLogKind.UNPLANNED), False)))
    doc.add(
        "Decisions",
        _grouped(ctx, ctx.log_items(by_kind(WorkLogKind.DECISION), False)),
        note_if_empty="decisions",
    )
    doc.add(
        "Blockers",
        _grouped(
            ctx,
            ctx.log_items(by_kind(WorkLogKind.BLOCKER), False)
            + [(t.project.name, ctx.task_line(t, "blocked")) for t in blocked],
        ),
        note_if_empty="blockers",
    )
    doc.add(
        "Research",
        _grouped(ctx, ctx.log_items(by_kind(WorkLogKind.RESEARCH), False)),
        note_if_empty="research",
    )
    doc.add(f"Next steps ({_fmt(nxt)})", _tasks(ctx, next_steps))
    return doc.render("today")


def weekly(ctx: _Ctx) -> list[str]:
    done = ctx.completed()
    done_ids = {t.id for t in done}
    planned = list(
        ctx.db.scalars(
            ctx.live().where(Task.scheduled_date >= ctx.start, Task.scheduled_date <= ctx.end)
        ).unique()
    )
    planned_ids = {p.id for p in planned}
    outstanding = [t for t in planned if t.status not in DONE]
    planned_done = [t for t in planned if t.id in done_ids]
    unplanned_done = [t for t in done if t.id not in planned_ids]
    logs = ctx.logs()
    hours_logged = sum(float(w.hours or 0) for w in logs)
    moved, created = ctx.changes()
    blocked = ctx.blocked()

    # Milestones with real movement this week, or due this week; future untouched ones are not
    # "progressed" (they appear under Coming up when due next week).
    touched = {t.milestone_id for t in done} | {
        t.milestone_id for tid in moved if (t := ctx.db.get(Task, tid))
    }
    nw_start, nw_end = ctx.end + timedelta(days=1), ctx.end + timedelta(days=7)
    ms_stmt = ctx.scope(
        select(Milestone).join(Project).where(Project.status != ProjectStatus.ARCHIVED),
        Milestone.project_id,
    ).order_by(Milestone.due_date.asc().nulls_last())
    ms_now, ms_next = [], []
    for m in ctx.db.scalars(ms_stmt):
        achieved = m.achieved_at and ctx.lo <= m.achieved_at < ctx.hi
        due_now = m.due_date and ctx.start <= m.due_date <= ctx.end
        if m.id in touched or achieved or due_now:
            ms_now.append(_milestone_line(ctx, m, " · **achieved this week**" if achieved else ""))
        elif m.due_date and nw_start <= m.due_date <= nw_end and m.status.value != "achieved":
            ms_next.append(_milestone_line(ctx, m))
    upcoming = list(
        ctx.db.scalars(
            ctx.live()
            .where(
                Task.status.not_in(DONE),
                ((Task.scheduled_date >= nw_start) & (Task.scheduled_date <= nw_end))
                | ((Task.due_date >= nw_start) & (Task.due_date <= nw_end)),
            )
            .order_by(Task.scheduled_date.asc().nulls_last(), Task.due_date.asc().nulls_last())
        ).unique()
    )
    overdue = list(
        ctx.db.scalars(
            ctx.live().where(
                Task.status.not_in(DONE), Task.due_date <= ctx.end, Task.due_date.is_not(None)
            )
        ).unique()
    )
    by_kind = lambda *k: [w for w in logs if w.kind in k]  # noqa: E731
    pct = f" ({len(planned_done) / len(planned) * 100:.0f}%)" if planned else ""
    doc = _Doc()
    doc.add(
        "At a glance",
        _glance(
            [
                f"- {_n(len(done), 'task')} completed ({len(planned_done)} planned, "
                f"{len(unplanned_done)} unplanned)",
                f"- {_n(len(outstanding), 'planned task')} still open" if planned else "",
                "- "
                + ", ".join(
                    x
                    for x in [
                        f"{_n(len(blocked), 'task')} blocked" if blocked else "",
                        f"{_n(len(overdue), 'task')} overdue" if overdue else "",
                    ]
                    if x
                )
                if blocked or overdue
                else "",
                f"- {_n(len(ms_now), 'milestone')} moved forward or due this week"
                if ms_now
                else "",
                f"- **{hours_logged:g}h** logged" if ctx.technical and hours_logged else "",
            ]
        ),
    )
    # Weekend completions count on the following Monday (working days are Monday to Friday).
    doc.add(
        "Achievements",
        _tasks(ctx, done, day=lambda t: working_day(t.completed_at.date())),
        note_if_empty="completed work",
    )
    doc.add("Milestones", _grouped(ctx, ms_now))
    pva = [
        f"- Tasks planned this week: **{len(planned)}**",
        f"- Planned tasks completed: **{len(planned_done)}**{pct}",
        f"- Unplanned tasks completed: **{len(unplanned_done)}**",
        f"- Planned tasks outstanding: **{len(outstanding)}**",
    ]
    if ctx.technical:
        est = sum(float(t.estimate_hours or 0) for t in planned)
        pva.append(f"- Estimated effort planned: **{est:g}h**; hours logged: **{hours_logged:g}h**")
    doc.add("Planned versus actual", pva)
    doc.add(
        "Still open from this week's plan",
        _tasks(ctx, outstanding, extra=lambda t: f"{t.progress}%" if t.progress else ""),
    )
    doc.add("Added to the plan", _added(ctx, created, done_ids))
    doc.add(
        "Blockers",
        _grouped(
            ctx,
            ctx.log_items(by_kind(WorkLogKind.BLOCKER), True)
            + [(t.project.name, ctx.task_line(t, "blocked")) for t in blocked],
        ),
        note_if_empty="blockers",
    )
    doc.add(
        "Risks",
        _tasks(ctx, overdue, extra=lambda t: f"overdue (due {_day(t.due_date)})"),
        note_if_empty="risks",
    )
    doc.add(
        "Decisions",
        _grouped(ctx, ctx.log_items(by_kind(WorkLogKind.DECISION), True)),
        note_if_empty="decisions",
    )
    doc.add(
        "Research",
        _grouped(ctx, ctx.log_items(by_kind(WorkLogKind.RESEARCH), True)),
        note_if_empty="research",
    )
    doc.add(
        "Coming up next week",
        _grouped(
            ctx,
            ms_next
            + [
                (
                    t.project.name,
                    ctx.task_line(
                        t, f"due {_day(t.due_date)}" if t.due_date else "", t.scheduled_date
                    ),
                )
                for t in upcoming
            ],
        ),
    )
    return doc.render("this week")


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
        "- Tasks: "
        + (", ".join(f"{STATUS_LABEL[k]} {v}" for k, v in sorted(counts.items())) or "none"),
    ]
    ms_lines, deliverables = [], []
    milestones = sorted(project.milestones, key=lambda m: m.due_date or date.max)
    for m in milestones:
        _, line = _milestone_line(ctx, m, f" · {m.status.value.replace('_', ' ')}")
        ms_lines.append(line)
        if (m.deliverables or "").strip():
            deliverables.append(f"- {m.title}: {m.deliverables.strip()}")
    outstanding = [t for t in top if t.status not in DONE]
    outstanding.sort(key=lambda t: t.scheduled_date or t.due_date or date.max)
    # Outstanding work grouped by milestone, so the plan reads in order.
    by_ms: dict[str, list[str]] = defaultdict(list)
    ms_title = {m.id: m.title for m in milestones}
    for t in outstanding[:60]:
        when = t.scheduled_date or t.due_date
        extra = ", ".join(
            x for x in [f"{t.progress}%" if t.progress else "", _day(when) if when else ""] if x
        )
        by_ms[ms_title.get(t.milestone_id, "No milestone")].append(ctx.task_line(t, extra))
    order = [ms_title[m.id] for m in milestones if ms_title[m.id] in by_ms] + (
        ["No milestone"] if "No milestone" in by_ms else []
    )
    out_lines = []
    for name in order:
        out_lines += [f"### {name}", "", *by_ms[name], ""]
    logs = ctx.logs()
    doc = _Doc()
    doc.add("Overall progress", overview)
    doc.add("Objectives", [project.objectives.strip()] if project.objectives else [])
    doc.add("Milestones", ms_lines, note_if_empty="milestones")
    doc.add("Deliverables", deliverables)
    doc.add(
        f"Outstanding work ({len(outstanding)} {'task' if len(outstanding) == 1 else 'tasks'}"
        + (", first 60 shown" if len(outstanding) > 60 else "")
        + ")",
        out_lines[:-1],
    )
    doc.add(
        "Risks and assumptions",
        [project.risks_assumptions.strip()] if project.risks_assumptions else [],
        note_if_empty="risks",
    )
    doc.add(
        "Decisions",
        [
            line
            for _, line in ctx.log_items([w for w in logs if w.kind == WorkLogKind.DECISION], True)
        ],
        note_if_empty="decisions",
    )
    doc.add(
        "Blockers",
        [ctx.task_line(t) for t in tasks if t.status == TaskStatus.BLOCKED],
        note_if_empty="blockers",
    )
    return doc.render("for this project")


def _title(kind: str, ctx: _Ctx, project: Project | None) -> str:
    scope = f" — {project.name}" if project else ""
    if kind == "daily":
        return f"Daily report{scope}: {_fmt(ctx.start)}"
    if kind == "weekly":
        return f"Weekly report{scope}: w/c {_fmt(ctx.start)}"
    return f"Project report{scope}: {_fmt(ctx.end)}"


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
