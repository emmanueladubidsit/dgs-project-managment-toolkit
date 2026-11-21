import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MilestoneStatus, Priority, ProjectStatus


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Stages ----------
class StageIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None
    position: int = 0
    is_active: bool = True


class StageOut(ORM):
    id: uuid.UUID
    name: str
    description: str | None
    position: int
    is_active: bool


# ---------- Projects ----------
class ProjectBase(BaseModel):
    description: str | None = None
    problem_statement: str | None = None
    objectives: str | None = None
    target_users: str | None = None
    business_context: str | None = None
    scope: str | None = None
    out_of_scope: str | None = None
    expected_outcomes: str | None = None
    stakeholders: str | None = None
    dependencies: str | None = None
    risks_assumptions: str | None = None
    tech_stack: str | None = None
    repository_url: str | None = Field(default=None, max_length=500)
    docs_location: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    start_date: date | None = None
    target_date: date | None = None
    priority: Priority = Priority.MEDIUM
    stage_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.start_date and self.target_date and self.target_date < self.start_date:
            raise ValueError("Target completion date cannot be before the start date.")
        return self


class ProjectCreate(ProjectBase):
    name: str = Field(min_length=1, max_length=200)
    # Workstream names to create alongside the project (optional convenience).
    workstreams: list[str] = []


class ProjectUpdate(BaseModel):
    """Partial update: only supplied fields change."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    problem_statement: str | None = None
    objectives: str | None = None
    target_users: str | None = None
    business_context: str | None = None
    scope: str | None = None
    out_of_scope: str | None = None
    expected_outcomes: str | None = None
    stakeholders: str | None = None
    dependencies: str | None = None
    risks_assumptions: str | None = None
    tech_stack: str | None = None
    repository_url: str | None = Field(default=None, max_length=500)
    docs_location: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    start_date: date | None = None
    target_date: date | None = None
    priority: Priority | None = None
    status: ProjectStatus | None = None
    stage_id: uuid.UUID | None = None


class ProgressBreakdown(BaseModel):
    percent: float
    method: str
    explanation: str
    tasks_counted: int
    tasks_completed: int
    tasks_excluded: int
    total_weight: float


class ProjectOut(ORM, ProjectBase):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    stage: StageOut | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectSummary(ProjectOut):
    progress: ProgressBreakdown
    task_counts: dict[str, int]
    overdue_count: int
    blocked_count: int


# ---------- Workstreams ----------
class WorkstreamIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    position: int | None = None


class WorkstreamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    position: int | None = None


class WorkstreamOut(ORM):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: str | None
    position: int


# ---------- Milestones ----------
class MilestoneIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    deliverables: str | None = None
    due_date: date | None = None
    workstream_id: uuid.UUID | None = None
    status: MilestoneStatus = MilestoneStatus.PLANNED


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    deliverables: str | None = None
    due_date: date | None = None
    workstream_id: uuid.UUID | None = None
    status: MilestoneStatus | None = None


class MilestoneOut(ORM):
    id: uuid.UUID
    project_id: uuid.UUID
    workstream_id: uuid.UUID | None
    title: str
    description: str | None
    deliverables: str | None
    due_date: date | None
    status: MilestoneStatus
    achieved_at: datetime | None
    created_at: datetime


class MilestoneSummary(MilestoneOut):
    project_name: str
    progress: ProgressBreakdown
    warnings: list[str]
