"""Daily, weekly and monthly planning, delivery-plan checks and work logs.

Which tasks are planned for a day is stored on Task.scheduled_date, so the Kanban board,
task list and planner always show the same records."""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.projects import _get_project, _milestone_summaries
from app.db import get_db
from app.errors import bad_request, not_found
from app.models import Milestone, PlanNote, Project, Task, TaskDependency, WorkLog
from app.models.enums import MilestoneStatus, PlanPeriod, ProjectStatus, TaskStatus
from app.schemas.planning import (
    Capacity,
    CarryForwardIn,
    DayPlan,
    MonthPlan,
    MonthWeek,
    PlanCheck,
    PlanNoteIn,
    PlanNoteOut,
    WeekDay,
    WeekPlan,
    WorkLogIn,
    WorkLogOut,
    WorkLogUpdate,
)
from app.schemas.task import TaskOut
from app.services.tasks import DONE, serialise, update_task

router = APIRouter(tags=["planning"])


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return start, nxt - timedelta(days=1)


def _live_tasks():
    return (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .where(Task.archived_at.is_(None), Project.status != ProjectStatus.ARCHIVED)
    )


def _tasks(db: Session, stmt) -> list[TaskOut]:
    return serialise(db, list(db.scalars(stmt).unique()))


def _day_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    tz = datetime.now().astimezone().tzinfo
    return (
        datetime.combine(start, time.min, tzinfo=tz),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
    )


def _note(db: Session, period: PlanPeriod, start: date) -> PlanNote | None:
    return db.scalar(
        select(PlanNote).where(PlanNote.period == period, PlanNote.period_start == start)
    )


def _hours(tasks: list[TaskOut]) -> tuple[float, int]:
    open_tasks = [t for t in tasks if t.status not in DONE]
    return (
        float(sum(t.estimate_hours or 0 for t in open_tasks)),
        sum(1 for t in open_tasks if t.estimate_hours is None),
    )


def _capacity(planned: float, available: Decimal | None, unestimated: int) -> Capacity:
    avail = float(available) if available is not None else None
    if avail is None:
        msg = "Working hours have not been set for this day, so capacity is not checked."
        over = False
    else:
        over = planned > avail
        msg = f"{planned:g}h planned against {avail:g}h available" + (
            " — over capacity." if over else "."
        )
    if unestimated:
        msg += f" {unestimated} task(s) have no estimate."
    return Capacity(
        planned_hours=planned,
        available_hours=avail,
        unestimated_tasks=unestimated,
        over_capacity=over,
        message=msg,
    )


def _work_logs(db: Session, start: date, end: date, project_id=None) -> list[WorkLogOut]:
    stmt = (
        select(WorkLog)
        .where(WorkLog.entry_date >= start, WorkLog.entry_date <= end)
        .order_by(WorkLog.entry_date, WorkLog.created_at)
    )
    if project_id:
        stmt = stmt.where(WorkLog.project_id == project_id)
    return [_log_out(w) for w in db.scalars(stmt)]


def _log_out(w: WorkLog) -> WorkLogOut:
    return WorkLogOut.model_validate(
        {
            **{k: getattr(w, k) for k in WorkLogOut.model_fields if hasattr(w, k)},
            "project_name": w.project.name if w.project else None,
            "task_title": w.task.title if w.task else None,
        }
    )


# ---------------------------------------------------------------- planner views
@router.get("/planner/day", response_model=DayPlan)
def day_plan(day: date = Query(alias="date"), db: Session = Depends(get_db)):
    lo, hi = _day_bounds(day, day)
    scheduled = _tasks(db, _live_tasks().where(Task.scheduled_date == day).order_by(Task.position))
    carried = _tasks(
        db,
        _live_tasks()
        .where(Task.scheduled_date < day, Task.status.not_in(DONE))
        .order_by(Task.scheduled_date, Task.position),
    )
    due = _tasks(
        db,
        _live_tasks().where(
            Task.due_date == day,
            Task.status.not_in(DONE),
            (Task.scheduled_date.is_(None)) | (Task.scheduled_date != day),
        ),
    )
    completed = _tasks(db, _live_tasks().where(Task.completed_at >= lo, Task.completed_at < hi))
    note = _note(db, PlanPeriod.DAY, day)
    planned, unestimated = _hours(scheduled)
    return DayPlan(
        date=day,
        note=PlanNoteOut.model_validate(note) if note else None,
        scheduled=scheduled,
        carried_over=carried,
        due_unscheduled=due,
        completed=completed,
        blockers=[
            t for t in scheduled + carried if t.status == TaskStatus.BLOCKED or t.open_dependencies
        ],
        work_logs=_work_logs(db, day, day),
        capacity=_capacity(planned, note.available_hours if note else None, unestimated),
    )


@router.get("/planner/week", response_model=WeekPlan)
def week_plan(
    start: date = Query(description="Any day in the week"), db: Session = Depends(get_db)
):
    ws = week_start(start)
    we = ws + timedelta(days=6)
    lo, hi = _day_bounds(ws, we)
    in_week = _tasks(
        db,
        _live_tasks()
        .where(Task.scheduled_date >= ws, Task.scheduled_date <= we)
        .order_by(Task.scheduled_date, Task.position),
    )
    by_day: dict[date, list[TaskOut]] = defaultdict(list)
    for t in in_week:
        by_day[t.scheduled_date].append(t)
    day_notes = {
        n.period_start: n
        for n in db.scalars(
            select(PlanNote).where(
                PlanNote.period == PlanPeriod.DAY,
                PlanNote.period_start >= ws,
                PlanNote.period_start <= we,
            )
        )
    }
    days = []
    for i in range(7):
        d = ws + timedelta(days=i)
        hours, _ = _hours(by_day[d])
        n = day_notes.get(d)
        days.append(
            WeekDay(
                date=d,
                tasks=by_day[d],
                planned_hours=hours,
                available_hours=float(n.available_hours)
                if n and n.available_hours is not None
                else None,
            )
        )
    completed_ids = set(
        db.scalars(
            select(Task.id).where(
                Task.completed_at >= lo, Task.completed_at < hi, Task.archived_at.is_(None)
            )
        )
    )
    planned_ids = {t.id for t in in_week}
    milestones = db.scalars(
        select(Milestone)
        .join(Project)
        .where(
            Project.status != ProjectStatus.ARCHIVED,
            Milestone.due_date >= ws,
            Milestone.due_date <= we + timedelta(days=7),
            Milestone.status.in_([MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS]),
        )
        .order_by(Milestone.due_date)
    ).all()
    note = _note(db, PlanPeriod.WEEK, ws)
    return WeekPlan(
        week_start=ws,
        week_end=we,
        note=PlanNoteOut.model_validate(note) if note else None,
        days=days,
        carried_over=_tasks(
            db,
            _live_tasks()
            .where(Task.scheduled_date < ws, Task.status.not_in(DONE))
            .order_by(Task.scheduled_date),
        ),
        deadlines=_tasks(
            db,
            _live_tasks()
            .where(Task.due_date >= ws, Task.due_date <= we, Task.status.not_in(DONE))
            .order_by(Task.due_date),
        ),
        milestones=_milestone_summaries(db, list(milestones)),
        planned_count=len(planned_ids),
        completed_count=len(planned_ids & completed_ids),
        completed_unplanned_count=len(completed_ids - planned_ids),
    )


@router.get("/planner/month", response_model=MonthPlan)
def month_plan(
    month: date = Query(description="Any day in the month"), db: Session = Depends(get_db)
):
    ms, me = month_bounds(month)
    lo, hi = _day_bounds(ms, me)
    milestones = db.scalars(
        select(Milestone)
        .join(Project)
        .where(
            Project.status != ProjectStatus.ARCHIVED,
            Milestone.due_date >= ms,
            Milestone.due_date <= me,
        )
        .order_by(Milestone.due_date)
    ).all()
    scheduled = list(
        db.scalars(_live_tasks().where(Task.scheduled_date >= ms, Task.scheduled_date <= me))
    )
    completed = list(
        db.scalars(select(Task).where(Task.completed_at >= lo, Task.completed_at < hi))
    )
    weeks = []
    w = week_start(ms)
    while w <= me:
        we = w + timedelta(days=6)
        wlo, whi = _day_bounds(w, we)
        weeks.append(
            MonthWeek(
                week_start=w,
                planned=sum(1 for t in scheduled if w <= t.scheduled_date <= we),
                completed=sum(1 for t in completed if wlo <= t.completed_at < whi),
            )
        )
        w += timedelta(days=7)
    note = _note(db, PlanPeriod.MONTH, ms)
    return MonthPlan(
        month_start=ms,
        month_end=me,
        note=PlanNoteOut.model_validate(note) if note else None,
        milestones=_milestone_summaries(db, list(milestones)),
        deadlines=_tasks(
            db,
            _live_tasks()
            .where(Task.due_date >= ms, Task.due_date <= me, Task.status.not_in(DONE))
            .order_by(Task.due_date),
        ),
        weeks=weeks,
        completed_count=len(completed),
        planned_count=len(scheduled),
    )


@router.put("/planner/notes", response_model=PlanNoteOut)
def upsert_note(body: PlanNoteIn, db: Session = Depends(get_db)):
    start = body.period_start
    if body.period == PlanPeriod.WEEK:
        start = week_start(start)
    elif body.period == PlanPeriod.MONTH:
        start = start.replace(day=1)
    note = _note(db, body.period, start) or PlanNote(period=body.period, period_start=start)
    note.objectives, note.notes, note.available_hours = (
        body.objectives,
        body.notes,
        body.available_hours,
    )
    db.add(note)
    db.commit()
    return note


@router.post("/planner/carry-forward", response_model=list[TaskOut])
def carry_forward(body: CarryForwardIn, db: Session = Depends(get_db)):
    """Reschedule unfinished tasks planned before `to_date` onto `to_date`."""
    stmt = select(Task).where(
        Task.scheduled_date < body.to_date,
        Task.status.not_in(DONE),
        Task.archived_at.is_(None),
    )
    if body.task_ids is not None:
        stmt = stmt.where(Task.id.in_(body.task_ids))
    tasks = list(db.scalars(stmt))
    for t in tasks:
        update_task(db, t, {"scheduled_date": body.to_date})
    db.commit()
    return serialise(db, tasks)


# ---------------------------------------------------------------- delivery checks
@router.get("/projects/{project_id}/plan-check", response_model=list[PlanCheck])
def plan_check(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """Deterministic checks for gaps and risks in a project's delivery plan."""
    project = _get_project(db, project_id)
    tasks = list(
        db.scalars(select(Task).where(Task.project_id == project_id, Task.archived_at.is_(None)))
    )
    open_tasks = [t for t in tasks if t.status not in DONE]
    milestones = list(project.milestones)
    checks: list[PlanCheck] = []

    def add(category, message, task_ids=(), milestone_ids=(), severity="warning"):
        checks.append(
            PlanCheck(
                severity=severity,
                category=category,
                message=message,
                task_ids=list(task_ids),
                milestone_ids=list(milestone_ids),
            )
        )

    if not tasks:
        add("missing_tasks", "This project has no tasks yet.", severity="info")
    no_ac = [t.id for t in open_tasks if not (t.acceptance_criteria or "").strip()]
    if no_ac:
        add("acceptance_criteria", f"{len(no_ac)} open task(s) have no acceptance criteria.", no_ac)
    no_est = [t.id for t in open_tasks if t.estimate_hours is None]
    if no_est:
        add(
            "estimates",
            f"{len(no_est)} open task(s) have no effort estimate.",
            no_est,
            severity="info",
        )
    no_deliv = [m.id for m in milestones if not (m.deliverables or "").strip()]
    if no_deliv:
        add(
            "deliverables",
            f"{len(no_deliv)} milestone(s) have no deliverables defined.",
            milestone_ids=no_deliv,
        )
    linked = {t.milestone_id for t in tasks}
    empty = [m.id for m in milestones if m.id not in linked]
    if empty:
        add(
            "missing_tasks", f"{len(empty)} milestone(s) have no tasks linked.", milestone_ids=empty
        )
    if project.target_date:
        late = [t.id for t in open_tasks if t.due_date and t.due_date > project.target_date]
        if late:
            add("deadlines", f"{len(late)} task(s) are due after the project target date.", late)
        late_ms = [m.id for m in milestones if m.due_date and m.due_date > project.target_date]
        if late_ms:
            add(
                "deadlines",
                f"{len(late_ms)} milestone(s) fall after the project target date.",
                milestone_ids=late_ms,
            )
    by_id = {t.id: t for t in tasks}
    deps = db.execute(
        select(TaskDependency.task_id, TaskDependency.depends_on_id).where(
            TaskDependency.task_id.in_(list(by_id))
        )
    ).all()
    clash = [
        a
        for a, b in deps
        if a in by_id
        and b in by_id
        and by_id[a].due_date
        and by_id[b].due_date
        and by_id[a].due_date < by_id[b].due_date
        and by_id[a].status not in DONE
    ]
    if clash:
        add("dependencies", f"{len(clash)} task(s) are due before the tasks they depend on.", clash)
    dependents = defaultdict(int)
    for _, b in deps:
        dependents[b] += 1
    bottlenecks = [
        tid
        for tid, n in dependents.items()
        if n >= 3 and by_id.get(tid) and by_id[tid].status not in DONE
    ]
    if bottlenecks:
        add(
            "bottlenecks",
            f"{len(bottlenecks)} unfinished task(s) block three or more others.",
            bottlenecks,
        )
    # Daily workload against available hours, where hours have been recorded.
    sched = defaultdict(float)
    for t in open_tasks:
        if t.scheduled_date and t.estimate_hours:
            sched[t.scheduled_date] += float(t.estimate_hours)
    if sched:
        notes = {
            n.period_start: n.available_hours
            for n in db.scalars(
                select(PlanNote).where(
                    PlanNote.period == PlanPeriod.DAY, PlanNote.period_start.in_(list(sched))
                )
            )
        }
        over = [d for d, h in sched.items() if notes.get(d) is not None and h > float(notes[d])]
        if over:
            add(
                "workload",
                f"Planned work exceeds available hours on {len(over)} day(s): "
                + ", ".join(d.strftime("%d %b") for d in sorted(over))
                + ".",
            )
    overdue = [t.id for t in open_tasks if t.due_date and t.due_date < date.today()]
    if overdue:
        add("deadlines", f"{len(overdue)} task(s) are overdue.", overdue)
    return checks


# ---------------------------------------------------------------- work logs
@router.get("/work-logs", response_model=list[WorkLogOut])
def list_work_logs(
    date_from: date | None = None,
    date_to: date | None = None,
    project_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(WorkLog).order_by(WorkLog.entry_date.desc(), WorkLog.created_at.desc())
    if date_from:
        stmt = stmt.where(WorkLog.entry_date >= date_from)
    if date_to:
        stmt = stmt.where(WorkLog.entry_date <= date_to)
    if project_id:
        stmt = stmt.where(WorkLog.project_id == project_id)
    return [_log_out(w) for w in db.scalars(stmt.limit(500))]


def _validate_log_refs(db: Session, data: dict) -> None:
    task = db.get(Task, data["task_id"]) if data.get("task_id") else None
    if data.get("task_id") and not task:
        raise bad_request("Task does not exist.")
    if data.get("project_id") and not db.get(Project, data["project_id"]):
        raise bad_request("Project does not exist.")
    if task:
        if data.get("project_id") and data["project_id"] != task.project_id:
            raise bad_request("Task does not belong to the selected project.")
        data["project_id"] = task.project_id


@router.post("/work-logs", response_model=WorkLogOut, status_code=201)
def create_work_log(body: WorkLogIn, db: Session = Depends(get_db)):
    data = body.model_dump()
    _validate_log_refs(db, data)
    log = WorkLog(**data)
    db.add(log)
    db.commit()
    db.refresh(log)
    return _log_out(log)


@router.patch("/work-logs/{log_id}", response_model=WorkLogOut)
def update_work_log(log_id: uuid.UUID, body: WorkLogUpdate, db: Session = Depends(get_db)):
    log = db.get(WorkLog, log_id)
    if not log:
        raise not_found("Work log")
    changes = body.model_dump(exclude_unset=True)
    merged = {"task_id": log.task_id, "project_id": log.project_id, **changes}
    _validate_log_refs(db, merged)
    changes["project_id"] = merged["project_id"]
    for k, v in changes.items():
        setattr(log, k, v)
    db.commit()
    db.refresh(log)
    return _log_out(log)


@router.delete("/work-logs/{log_id}", status_code=204)
def delete_work_log(log_id: uuid.UUID, db: Session = Depends(get_db)):
    log = db.get(WorkLog, log_id)
    if not log:
        raise not_found("Work log")
    db.delete(log)
    db.commit()
    return Response(status_code=204)
