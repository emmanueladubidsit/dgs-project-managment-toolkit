import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.db import get_db
from app.errors import bad_request, not_found
from app.models import Project, Task, TaskActivity, TaskComment, TaskDependency
from app.models.enums import Priority, ProjectStatus, TaskStatus
from app.schemas.task import (
    ActivityOut,
    BulkTaskUpdate,
    CommentIn,
    CommentOut,
    DependencyIn,
    DependencyRef,
    TaskCreate,
    TaskDetail,
    TaskOut,
    TaskUpdate,
)
from app.services.tasks import (
    DONE,
    add_dependency,
    apply_status_rules,
    get_task,
    now,
    record,
    serialise,
    update_task,
    validate_refs,
)

router = APIRouter(tags=["tasks"])

PRIORITY_ORDER = case(
    {
        Priority.CRITICAL.value: 0,
        Priority.HIGH.value: 1,
        Priority.MEDIUM.value: 2,
        Priority.LOW.value: 3,
    },
    value=Task.priority,
)
STATUS_ORDER = case(
    {s.value: i for i, s in enumerate(TaskStatus)},
    value=Task.status,
)
SortKey = Literal["position", "priority", "due_date", "status", "project", "updated", "created"]


def _detail(db: Session, task: Task) -> TaskDetail:
    base = serialise(db, [task])[0]
    subtasks = db.scalars(
        select(Task)
        .where(Task.parent_id == task.id, Task.archived_at.is_(None))
        .order_by(Task.position, Task.created_at)
    ).all()
    deps = db.scalars(
        select(Task)
        .join(TaskDependency, TaskDependency.depends_on_id == Task.id)
        .where(TaskDependency.task_id == task.id)
    ).all()
    dependents = db.scalars(
        select(Task)
        .join(TaskDependency, TaskDependency.task_id == Task.id)
        .where(TaskDependency.depends_on_id == task.id)
    ).all()
    return TaskDetail(
        **base.model_dump(),
        subtasks=serialise(db, list(subtasks)),
        dependencies=[DependencyRef.model_validate(d) for d in deps],
        dependents=[DependencyRef.model_validate(d) for d in dependents],
    )


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: uuid.UUID | None = None,
    workstream_id: uuid.UUID | None = None,
    milestone_id: uuid.UUID | None = None,
    parent_id: uuid.UUID | None = None,
    top_level: bool = False,
    status: list[TaskStatus] = Query(default=[]),
    priority: list[Priority] = Query(default=[]),
    label: str | None = None,
    q: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    scheduled_from: date | None = None,
    scheduled_to: date | None = None,
    unscheduled: bool = False,
    overdue: bool = False,
    blocked: bool = False,
    include_archived: bool = False,
    include_archived_projects: bool = False,
    sort: SortKey = "position",
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
):
    stmt = select(Task).join(Project, Project.id == Task.project_id)
    if not include_archived:
        stmt = stmt.where(Task.archived_at.is_(None))
    if not include_archived_projects and not project_id:
        stmt = stmt.where(Project.status != ProjectStatus.ARCHIVED)
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    if workstream_id:
        stmt = stmt.where(Task.workstream_id == workstream_id)
    if milestone_id:
        stmt = stmt.where(Task.milestone_id == milestone_id)
    if parent_id:
        stmt = stmt.where(Task.parent_id == parent_id)
    elif top_level:
        stmt = stmt.where(Task.parent_id.is_(None))
    if status:
        stmt = stmt.where(Task.status.in_(status))
    if priority:
        stmt = stmt.where(Task.priority.in_(priority))
    if label:
        stmt = stmt.where(Task.labels.any(label))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Task.title.ilike(like), Task.description.ilike(like)))
    if due_from:
        stmt = stmt.where(Task.due_date >= due_from)
    if due_to:
        stmt = stmt.where(Task.due_date <= due_to)
    if scheduled_from:
        stmt = stmt.where(Task.scheduled_date >= scheduled_from)
    if scheduled_to:
        stmt = stmt.where(Task.scheduled_date <= scheduled_to)
    if unscheduled:
        stmt = stmt.where(Task.scheduled_date.is_(None))
    if overdue:
        stmt = stmt.where(Task.due_date < date.today(), Task.status.not_in(DONE))
    if blocked:
        # Blocked = explicitly Blocked, or waiting on an unfinished dependency.
        dep_task = aliased(Task)
        open_dep = (
            select(func.count())
            .select_from(TaskDependency)
            .join(dep_task, dep_task.id == TaskDependency.depends_on_id)
            .where(TaskDependency.task_id == Task.id, dep_task.status.not_in(DONE))
            .correlate(Task)
            .scalar_subquery()
        )
        stmt = stmt.where(
            Task.status.not_in(DONE),
            or_(Task.status == TaskStatus.BLOCKED, open_dep > 0),
        )
    order = {
        "position": [Task.position, Task.created_at],
        "priority": [PRIORITY_ORDER, Task.due_date.asc().nulls_last()],
        "due_date": [Task.due_date.asc().nulls_last(), PRIORITY_ORDER],
        "status": [STATUS_ORDER, PRIORITY_ORDER],
        "project": [Project.name, Task.position],
        "updated": [Task.updated_at.desc()],
        "created": [Task.created_at.desc()],
    }[sort]
    tasks = list(db.scalars(stmt.order_by(*order).limit(limit)).unique())
    return serialise(db, tasks)


@router.post("/tasks", response_model=TaskDetail, status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    project = db.get(Project, body.project_id)
    if not project:
        raise bad_request("Project does not exist.")
    data = body.model_dump()
    validate_refs(db, project.id, data)
    status = data.pop("status")
    # New tasks go to the bottom of their column.
    max_pos = db.scalar(
        select(func.max(Task.position)).where(Task.project_id == project.id, Task.status == status)
    )
    task = Task(**data, status=TaskStatus.TODO, position=(max_pos or 0) + 1000)
    if status != TaskStatus.TODO:
        apply_status_rules(task, status)
    db.add(task)
    db.flush()
    record(db, task, "created", {"title": [None, task.title]})
    db.commit()
    db.refresh(task)
    return _detail(db, task)


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def read_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    return _detail(db, get_task(db, task_id))


@router.patch("/tasks/{task_id}", response_model=TaskDetail)
def patch_task(task_id: uuid.UUID, body: TaskUpdate, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    changes = body.model_dump(exclude_unset=True)
    if "title" in changes and changes["title"] is None:
        raise bad_request("Title cannot be empty.")
    for f in ("status", "priority", "progress", "labels"):
        if f in changes and changes[f] is None:
            changes.pop(f)
    start = changes.get("start_date", task.start_date)
    due = changes.get("due_date", task.due_date)
    if start and due and due < start:
        raise bad_request("Due date cannot be before the start date.")
    update_task(db, task, changes)
    db.commit()
    db.refresh(task)
    return _detail(db, task)


@router.post("/tasks/bulk", response_model=list[TaskOut])
def bulk_update(body: BulkTaskUpdate, db: Session = Depends(get_db)):
    changes = body.changes.model_dump(exclude_unset=True)
    disallowed = {"title", "parent_id", "description", "position"} & changes.keys()
    if disallowed:
        raise bad_request(f"Cannot bulk-update: {', '.join(sorted(disallowed))}.")
    tasks = list(db.scalars(select(Task).where(Task.id.in_(body.task_ids))))
    if len(tasks) != len(set(body.task_ids)):
        raise not_found("One or more tasks")
    for task in tasks:
        update_task(db, task, dict(changes))
    db.commit()
    return serialise(db, tasks)


@router.post("/tasks/{task_id}/archive", response_model=TaskDetail)
def archive_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    task.archived_at = now()
    record(db, task, "archived")
    db.commit()
    return _detail(db, task)


@router.post("/tasks/{task_id}/restore", response_model=TaskDetail)
def restore_task(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    task.archived_at = None
    record(db, task, "restored")
    db.commit()
    return _detail(db, task)


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: uuid.UUID,
    confirm: bool = Query(default=False, description="Must be true. Subtasks are also deleted."),
    db: Session = Depends(get_db),
):
    task = get_task(db, task_id)
    if not confirm:
        raise bad_request(
            "Deleting a task is permanent and removes its subtasks, comments and history. "
            "Confirm to continue, or archive it instead.",
            code="confirmation_required",
        )
    db.delete(task)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------- dependencies
@router.post("/tasks/{task_id}/dependencies", response_model=TaskDetail, status_code=201)
def create_dependency(task_id: uuid.UUID, body: DependencyIn, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    add_dependency(db, task, body.depends_on_id)
    db.commit()
    return _detail(db, task)


@router.delete("/tasks/{task_id}/dependencies/{depends_on_id}", response_model=TaskDetail)
def remove_dependency(task_id: uuid.UUID, depends_on_id: uuid.UUID, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    dep = db.scalar(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id, TaskDependency.depends_on_id == depends_on_id
        )
    )
    if not dep:
        raise not_found("Dependency")
    record(db, task, "dependency_removed", {"depends_on": [dep.depends_on.title, None]})
    db.delete(dep)
    db.commit()
    return _detail(db, task)


# ---------------------------------------------------------------- comments & history
@router.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
def list_comments(task_id: uuid.UUID, db: Session = Depends(get_db)):
    get_task(db, task_id)
    return db.scalars(
        select(TaskComment).where(TaskComment.task_id == task_id).order_by(TaskComment.created_at)
    ).all()


@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(task_id: uuid.UUID, body: CommentIn, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    comment = TaskComment(task_id=task_id, body=body.body.strip())
    db.add(comment)
    record(db, task, "commented", {"comment": [None, comment.body[:200]]})
    db.commit()
    return comment


@router.get("/tasks/{task_id}/activity", response_model=list[ActivityOut])
def task_activity(task_id: uuid.UUID, db: Session = Depends(get_db)):
    get_task(db, task_id)
    return db.scalars(
        select(TaskActivity)
        .where(TaskActivity.task_id == task_id)
        .order_by(TaskActivity.created_at.desc())
    ).all()


@router.get("/activity", response_model=list[ActivityOut])
def recent_activity(
    project_id: uuid.UUID | None = None,
    limit: int = Query(default=30, le=200),
    db: Session = Depends(get_db),
):
    stmt = (
        select(TaskActivity, Task.title)
        .join(Task, Task.id == TaskActivity.task_id)
        .order_by(TaskActivity.created_at.desc())
        .limit(limit)
    )
    if project_id:
        stmt = stmt.where(TaskActivity.project_id == project_id)
    return [
        ActivityOut.model_validate({**ActivityOut.model_validate(a).model_dump(), "task_title": t})
        for a, t in db.execute(stmt)
    ]
