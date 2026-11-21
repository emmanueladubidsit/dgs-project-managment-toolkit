import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import Priority, TaskStatus


class TaskFields(BaseModel):
    description: str | None = None
    workstream_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    start_date: date | None = None
    due_date: date | None = None
    scheduled_date: date | None = None
    estimate_hours: Decimal | None = Field(default=None, ge=0, le=9999)
    actual_hours: Decimal | None = Field(default=None, ge=0, le=9999)
    progress: int = Field(default=0, ge=0, le=100)
    weight: int | None = Field(default=None, ge=1, le=100)
    acceptance_criteria: str | None = None
    deliverables: str | None = None
    assignee: str | None = Field(default=None, max_length=120)
    labels: list[str] = []
    notes: str | None = None

    @field_validator("labels")
    @classmethod
    def _clean_labels(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for label in v:
            label = label.strip()[:60]
            if label and label not in out:
                out.append(label)
        return out

    @model_validator(mode="after")
    def _dates_in_order(self):
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValueError("Due date cannot be before the start date.")
        return self


class TaskCreate(TaskFields):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=300)


class TaskUpdate(BaseModel):
    """Partial update. Fields omitted are unchanged; explicit null clears a field."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    workstream_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: Priority | None = None
    start_date: date | None = None
    due_date: date | None = None
    scheduled_date: date | None = None
    estimate_hours: Decimal | None = Field(default=None, ge=0, le=9999)
    actual_hours: Decimal | None = Field(default=None, ge=0, le=9999)
    progress: int | None = Field(default=None, ge=0, le=100)
    weight: int | None = Field(default=None, ge=1, le=100)
    acceptance_criteria: str | None = None
    deliverables: str | None = None
    assignee: str | None = Field(default=None, max_length=120)
    labels: list[str] | None = None
    notes: str | None = None
    position: float | None = None


class BulkTaskUpdate(BaseModel):
    task_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)
    changes: TaskUpdate


class RefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class DependencyRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    status: TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    workstream_id: uuid.UUID | None
    workstream_name: str | None
    milestone_id: uuid.UUID | None
    milestone_title: str | None
    parent_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    start_date: date | None
    due_date: date | None
    scheduled_date: date | None
    estimate_hours: Decimal | None
    actual_hours: Decimal | None
    progress: int
    weight: int | None
    acceptance_criteria: str | None
    deliverables: str | None
    assignee: str | None
    labels: list[str]
    notes: str | None
    position: float
    completed_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # Derived
    is_overdue: bool
    subtask_count: int
    subtasks_completed: int
    open_dependencies: list[DependencyRef]


class TaskDetail(TaskOut):
    subtasks: list[TaskOut]
    dependencies: list[DependencyRef]
    dependents: list[DependencyRef]


class DependencyIn(BaseModel):
    depends_on_id: uuid.UUID


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=20000)


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    task_id: uuid.UUID
    body: str
    created_at: datetime


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    task_id: uuid.UUID
    project_id: uuid.UUID
    action: str
    changes: dict
    created_at: datetime
    task_title: str | None = None
