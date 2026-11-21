import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.models.enums import Priority, TaskStatus, str_enum


class Task(IdMixin, TimestampMixin, Base):
    """A unit of work. Subtasks are tasks with a parent_id (Project → Workstream →
    Milestone → Task → Subtask). Status and progress are deliberately independent."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),
        CheckConstraint("weight IS NULL OR (weight >= 1 AND weight <= 100)", name="weight_range"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
        Index("ix_tasks_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    workstream_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workstreams.id", ondelete="SET NULL"), index=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL"), index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        str_enum(TaskStatus, "task_status"), default=TaskStatus.TODO
    )
    priority: Mapped[Priority] = mapped_column(
        str_enum(Priority, "task_priority"), default=Priority.MEDIUM
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    # The day the work is planned for in the daily/weekly planner.
    scheduled_date: Mapped[date | None] = mapped_column(Date, index=True)
    estimate_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    actual_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    # Optional explicit importance used in weighted progress (see services/progress.py).
    weight: Mapped[int | None] = mapped_column(Integer)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    deliverables: Mapped[str | None] = mapped_column(Text)
    assignee: Mapped[str | None] = mapped_column(String(120))
    labels: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    position: Mapped[float] = mapped_column(Float, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    subtasks: Mapped[list["Task"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan", order_by="Task.position"
    )
    parent: Mapped["Task | None"] = relationship(back_populates="subtasks", remote_side="Task.id")
    project = relationship("Project", lazy="joined")
    workstream = relationship("Workstream", lazy="joined")
    milestone = relationship("Milestone", lazy="joined")


class TaskDependency(IdMixin, Base):
    """task_id cannot be finished until depends_on_id is completed."""

    __tablename__ = "task_dependencies"
    __table_args__ = (
        UniqueConstraint("task_id", "depends_on_id", name="uq_task_dependency_pair"),
        CheckConstraint("task_id <> depends_on_id", name="not_self"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    depends_on_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )

    depends_on: Mapped[Task] = relationship(foreign_keys=[depends_on_id], lazy="joined")


class TaskComment(IdMixin, TimestampMixin, Base):
    __tablename__ = "task_comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)


class TaskActivity(IdMixin, Base):
    """Append-only history of task changes."""

    __tablename__ = "task_activity"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(40))  # created, updated, commented, ...
    changes: Mapped[dict] = mapped_column(JSONB, default=dict)  # {field: [old, new]}
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone(), index=True
    )
