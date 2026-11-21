import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.models.enums import PlanPeriod, ReportKind, WorkLogKind, str_enum


class PlanNote(IdMixin, TimestampMixin, Base):
    """Objectives and notes for a day, week (starting Monday) or month (starting the 1st).
    Which tasks are planned is held on Task.scheduled_date, so there is one source of truth."""

    __tablename__ = "plan_notes"
    __table_args__ = (UniqueConstraint("period", "period_start", name="uq_plan_note_period"),)

    period: Mapped[PlanPeriod] = mapped_column(str_enum(PlanPeriod, "plan_period"))
    period_start: Mapped[date] = mapped_column(Date)
    objectives: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    available_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))


class WorkLog(IdMixin, TimestampMixin, Base):
    """A daily progress update, decision, blocker, research note or unplanned work entry."""

    __tablename__ = "work_logs"

    entry_date: Mapped[date] = mapped_column(Date, index=True)
    kind: Mapped[WorkLogKind] = mapped_column(
        str_enum(WorkLogKind, "work_log_kind"), default=WorkLogKind.PROGRESS
    )
    summary: Mapped[str] = mapped_column(Text)
    hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )

    project = relationship("Project", lazy="joined")
    task = relationship("Task", lazy="joined")


class Report(IdMixin, TimestampMixin, Base):
    """A saved, editable report. Content is generated from stored data, then editable."""

    __tablename__ = "reports"

    kind: Mapped[ReportKind] = mapped_column(str_enum(ReportKind, "report_kind"))
    title: Mapped[str] = mapped_column(String(300))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    content: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
