"""Task business rules: reference validation, status transitions, dependency cycle
prevention, change history and batched serialisation."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import bad_request, conflict, not_found
from app.models import Milestone, Task, TaskActivity, TaskDependency, Workstream
from app.models.enums import TaskStatus
from app.schemas.task import DependencyRef, TaskOut

TRACKED_FIELDS = {
    "title",
    "description",
    "workstream_id",
    "milestone_id",
    "parent_id",
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
    "assignee",
    "labels",
    "notes",
}
DONE = {TaskStatus.COMPLETED, TaskStatus.CANCELLED}


def now() -> datetime:
    return datetime.now().astimezone()


def get_task(db: Session, task_id: uuid.UUID) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise not_found("Task")
    return task


def _json(v: object) -> object:
    if isinstance(v, (uuid.UUID, date, datetime)):
        return str(v)
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "value"):
        return v.value
    return v


def record(db: Session, task: Task, action: str, changes: dict | None = None) -> None:
    db.add(
        TaskActivity(
            task_id=task.id, project_id=task.project_id, action=action, changes=changes or {}
        )
    )


def validate_refs(db: Session, project_id: uuid.UUID, values: dict, task_id=None) -> None:
    """Workstream, milestone and parent must belong to the same project; parent must not
    create a cycle."""
    if ws_id := values.get("workstream_id"):
        ws = db.get(Workstream, ws_id)
        if not ws or ws.project_id != project_id:
            raise bad_request("Workstream does not belong to this project.")
    if ms_id := values.get("milestone_id"):
        ms = db.get(Milestone, ms_id)
        if not ms or ms.project_id != project_id:
            raise bad_request("Milestone does not belong to this project.")
    if parent_id := values.get("parent_id"):
        if task_id and parent_id == task_id:
            raise bad_request("A task cannot be its own parent.")
        parent = db.get(Task, parent_id)
        if not parent or parent.project_id != project_id:
            raise bad_request("Parent task does not belong to this project.")
        # Walk up from the proposed parent; if we meet this task, it would form a loop.
        cursor = parent
        while cursor is not None and task_id:
            if cursor.id == task_id:
                raise bad_request("That parent would create a circular task hierarchy.")
            cursor = cursor.parent


def apply_status_rules(task: Task, new_status: TaskStatus) -> None:
    """Completion stamps completed_at and sets progress to 100%. Re-opening clears the
    completion date but keeps the recorded progress. Parents are never auto-completed."""
    if new_status == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
        task.completed_at = now()
        task.progress = 100
    elif new_status != TaskStatus.COMPLETED and task.status == TaskStatus.COMPLETED:
        task.completed_at = None
    task.status = new_status


def update_task(db: Session, task: Task, changes: dict) -> dict:
    """Apply a partial update, record history and return the diff."""
    validate_refs(db, task.project_id, changes, task_id=task.id)
    diff: dict[str, list] = {}
    status_change = changes.pop("status", None)
    for field, value in changes.items():
        old = getattr(task, field)
        if old != value:
            diff[field] = [_json(old), _json(value)]
            setattr(task, field, value)
    if status_change is not None and status_change != task.status:
        old_status, old_progress = task.status, task.progress
        apply_status_rules(task, status_change)  # completion wins: completed work is 100%
        diff["status"] = [_json(old_status), _json(task.status)]
        if task.progress != old_progress:
            diff["progress"] = [diff.get("progress", [old_progress])[0], task.progress]
    tracked = {k: v for k, v in diff.items() if k in TRACKED_FIELDS or k == "position"}
    if any(k != "position" for k in tracked):
        action = "status_changed" if list(tracked) == ["status"] else "updated"
        record(db, task, action, {k: v for k, v in tracked.items() if k != "position"})
    return diff


def add_dependency(db: Session, task: Task, depends_on_id: uuid.UUID) -> TaskDependency:
    if depends_on_id == task.id:
        raise bad_request("A task cannot depend on itself.")
    other = db.get(Task, depends_on_id)
    if not other:
        raise not_found("Dependency task")
    exists = db.scalar(
        select(TaskDependency).where(
            TaskDependency.task_id == task.id, TaskDependency.depends_on_id == depends_on_id
        )
    )
    if exists:
        raise conflict("This dependency already exists.")
    # Cycle check: does `other` (transitively) depend on `task`?
    frontier, seen = [depends_on_id], set()
    while frontier:
        current = frontier.pop()
        if current == task.id:
            raise bad_request("This dependency would create a circular dependency.")
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(
            db.scalars(
                select(TaskDependency.depends_on_id).where(TaskDependency.task_id == current)
            )
        )
    dep = TaskDependency(task_id=task.id, depends_on_id=depends_on_id)
    db.add(dep)
    record(db, task, "dependency_added", {"depends_on": [None, other.title]})
    return dep


def serialise(db: Session, tasks: list[Task], today: date | None = None) -> list[TaskOut]:
    """Serialise tasks with derived fields using a fixed number of queries."""
    if not tasks:
        return []
    today = today or date.today()
    ids = [t.id for t in tasks]
    sub_rows = db.execute(
        select(
            Task.parent_id,
            func.count(),
            func.count().filter(Task.status == TaskStatus.COMPLETED),
        )
        .where(Task.parent_id.in_(ids), Task.archived_at.is_(None))
        .group_by(Task.parent_id)
    ).all()
    sub = {pid: (total, done) for pid, total, done in sub_rows}
    dep_rows = db.execute(
        select(TaskDependency.task_id, Task)
        .join(Task, Task.id == TaskDependency.depends_on_id)
        .where(TaskDependency.task_id.in_(ids), Task.status.not_in(DONE))
    ).all()
    open_deps: dict[uuid.UUID, list[DependencyRef]] = {}
    for tid, dep in dep_rows:
        open_deps.setdefault(tid, []).append(DependencyRef.model_validate(dep))

    out = []
    for t in tasks:
        total, done = sub.get(t.id, (0, 0))
        out.append(
            TaskOut.model_validate(
                {
                    **{c: getattr(t, c) for c in TaskOut.model_fields if hasattr(t, c)},
                    "project_name": t.project.name,
                    "workstream_name": t.workstream.name if t.workstream else None,
                    "milestone_title": t.milestone.title if t.milestone else None,
                    "is_overdue": bool(t.due_date and t.due_date < today and t.status not in DONE),
                    "subtask_count": total,
                    "subtasks_completed": done,
                    "open_dependencies": open_deps.get(t.id, []),
                }
            )
        )
    return out
