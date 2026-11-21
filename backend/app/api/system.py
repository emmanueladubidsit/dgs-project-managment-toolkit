"""Dashboard aggregate plus health and administration endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.planning import _day_bounds, _live_tasks, _tasks, week_start
from app.api.projects import _milestone_summaries, _summaries
from app.api.tasks import PRIORITY_ORDER, recent_activity
from app.config import get_settings
from app.db import get_db
from app.models import Milestone, Project, Task, TaskDependency, WorkLog
from app.models.enums import MilestoneStatus, ProjectStatus, TaskStatus
from app.schemas.planning import Dashboard
from app.services.tasks import DONE

router = APIRouter()


@router.get("/dashboard", response_model=Dashboard, tags=["dashboard"])
def dashboard(db: Session = Depends(get_db)):
    today = date.today()
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.status == ProjectStatus.ACTIVE)
            .order_by(Project.updated_at.desc())
        ).unique()
    )
    open_ = _live_tasks().where(Task.status.not_in(DONE))
    open_dep = (
        select(TaskDependency.id)
        .join(dep := Task.__table__.alias("d"), dep.c.id == TaskDependency.depends_on_id)
        .where(TaskDependency.task_id == Task.id, dep.c.status.not_in([s.value for s in DONE]))
        .correlate(Task)
        .exists()
    )
    ws = week_start(today)
    lo, hi = _day_bounds(ws, ws + timedelta(days=6))
    planned_ids = set(
        db.scalars(
            select(Task.id).where(
                Task.scheduled_date >= ws,
                Task.scheduled_date <= ws + timedelta(days=6),
                Task.archived_at.is_(None),
            )
        )
    )
    completed_ids = set(
        db.scalars(select(Task.id).where(Task.completed_at >= lo, Task.completed_at < hi))
    )
    milestones = db.scalars(
        select(Milestone)
        .join(Project)
        .where(
            Project.status == ProjectStatus.ACTIVE,
            Milestone.status.in_([MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS]),
        )
        .order_by(Milestone.due_date.asc().nulls_last())
        .limit(6)
    ).all()
    return Dashboard(
        today=today,
        projects=_summaries(db, projects),
        due_today=_tasks(
            db,
            open_.where((Task.due_date == today) | (Task.scheduled_date == today)).order_by(
                PRIORITY_ORDER
            ),
        ),
        overdue=_tasks(db, open_.where(Task.due_date < today).order_by(Task.due_date)),
        upcoming=_tasks(
            db,
            open_.where(Task.due_date > today, Task.due_date <= today + timedelta(days=7)).order_by(
                Task.due_date
            ),
        ),
        blocked=_tasks(db, open_.where((Task.status == TaskStatus.BLOCKED) | open_dep)),
        milestones=_milestone_summaries(db, list(milestones)),
        recent_activity=recent_activity(limit=12, db=db),
        week_planned=len(planned_ids),
        week_completed=len(planned_ids & completed_ids),
    )


@router.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:  # noqa: BLE001 — report status, never the error detail
        database = "unavailable"
    return {
        "status": "ok" if database == "ok" else "degraded",
        "version": settings.app_version,
        "database": database,
    }


@router.get("/admin/system", tags=["admin"])
def system_info(db: Session = Depends(get_db)):
    """Diagnostic information for the administration area. Contains no secrets."""
    settings = get_settings()
    pg_version = db.scalar(text("SHOW server_version"))
    revision = db.scalar(text("SELECT version_num FROM alembic_version"))
    size = db.scalar(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
    counts = {
        "projects": db.scalar(select(func.count()).select_from(Project)),
        "tasks": db.scalar(select(func.count()).select_from(Task)),
        "milestones": db.scalar(select(func.count()).select_from(Milestone)),
        "work_logs": db.scalar(select(func.count()).select_from(WorkLog)),
    }
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "database": {"engine": f"PostgreSQL {pg_version}", "migration": revision, "size": size},
        "record_counts": counts,
        "integrations": _integrations(db),
    }


def _integrations(db: Session) -> dict:
    from app.services.ai.provider import load_config
    from app.services.transcription import get_provider

    cfg = load_config(db)
    ai = {"disabled": "off", "manual": "copy and paste with an AI chat"}.get(
        cfg.provider, f"{cfg.model or 'model not set'} via {cfg.base_url or 'address not set'}"
    )
    voice_ok, _ = get_provider().available()
    return {
        "ai": ai,
        "voice": "local Whisper" if voice_ok else "not installed (make voice)",
        "claude_code": "not configured",
    }
