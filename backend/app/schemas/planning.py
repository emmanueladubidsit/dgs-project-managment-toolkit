import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PlanPeriod, ReportKind, WorkLogKind
from app.schemas.project import MilestoneSummary, ProjectSummary
from app.schemas.task import ActivityOut, TaskOut


class PlanNoteIn(BaseModel):
    period: PlanPeriod
    period_start: date
    objectives: str | None = None
    notes: str | None = None
    available_hours: Decimal | None = Field(default=None, ge=0, le=744)


class PlanNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    period: PlanPeriod
    period_start: date
    objectives: str | None
    notes: str | None
    available_hours: Decimal | None


class WorkLogIn(BaseModel):
    entry_date: date
    kind: WorkLogKind = WorkLogKind.PROGRESS
    summary: str = Field(min_length=1, max_length=20000)
    hours: Decimal | None = Field(default=None, ge=0, le=24)
    project_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class WorkLogUpdate(BaseModel):
    entry_date: date | None = None
    kind: WorkLogKind | None = None
    summary: str | None = Field(default=None, min_length=1, max_length=20000)
    hours: Decimal | None = Field(default=None, ge=0, le=24)
    project_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class WorkLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    entry_date: date
    kind: WorkLogKind
    summary: str
    hours: Decimal | None
    project_id: uuid.UUID | None
    task_id: uuid.UUID | None
    project_name: str | None = None
    task_title: str | None = None
    created_at: datetime


class Capacity(BaseModel):
    planned_hours: float
    available_hours: float | None
    unestimated_tasks: int
    over_capacity: bool
    message: str


class DayPlan(BaseModel):
    date: date
    note: PlanNoteOut | None
    scheduled: list[TaskOut]
    carried_over: list[TaskOut]
    due_unscheduled: list[TaskOut]
    completed: list[TaskOut]
    blockers: list[TaskOut]
    work_logs: list[WorkLogOut]
    capacity: Capacity


class WeekDay(BaseModel):
    date: date
    tasks: list[TaskOut]
    planned_hours: float
    available_hours: float | None


class WeekPlan(BaseModel):
    week_start: date
    week_end: date
    note: PlanNoteOut | None
    days: list[WeekDay]
    carried_over: list[TaskOut]
    deadlines: list[TaskOut]
    milestones: list[MilestoneSummary]
    planned_count: int
    completed_count: int
    completed_unplanned_count: int


class MonthWeek(BaseModel):
    week_start: date
    planned: int
    completed: int


class MonthPlan(BaseModel):
    month_start: date
    month_end: date
    note: PlanNoteOut | None
    milestones: list[MilestoneSummary]
    deadlines: list[TaskOut]
    weeks: list[MonthWeek]
    completed_count: int
    planned_count: int


class CarryForwardIn(BaseModel):
    to_date: date
    task_ids: list[uuid.UUID] | None = None  # default: everything overdue in the planner


class PlanCheck(BaseModel):
    severity: Literal["warning", "info"]
    category: str
    message: str
    task_ids: list[uuid.UUID] = []
    milestone_ids: list[uuid.UUID] = []


class Dashboard(BaseModel):
    today: date
    projects: list[ProjectSummary]
    due_today: list[TaskOut]
    overdue: list[TaskOut]
    upcoming: list[TaskOut]
    blocked: list[TaskOut]
    milestones: list[MilestoneSummary]
    recent_activity: list[ActivityOut]
    week_planned: int
    week_completed: int


class ReportGenerateIn(BaseModel):
    kind: ReportKind
    date: date  # any day in the period; weekly reports use its Monday–Sunday week
    project_id: uuid.UUID | None = None
    audience: Literal["stakeholder", "technical"] = "stakeholder"


class ReportDraft(BaseModel):
    kind: ReportKind
    title: str
    period_start: date
    period_end: date
    project_id: uuid.UUID | None
    content: str
    generated_at: datetime


class ReportIn(ReportDraft):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=1)


class ReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = Field(default=None, min_length=1)


class ReportOut(ReportDraft):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
