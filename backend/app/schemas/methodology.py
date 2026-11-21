import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.methodology import (
    Classification,
    DeliverableStatus,
    MethodologyKind,
    MethodologyStatus,
)


class ActivityIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    instructions: str | None = None
    expected_output: str | None = None


class StageIn(BaseModel):
    # Client-side key so deliverables can refer to a stage before it has a database id.
    key: str | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    validation_criteria: str | None = None
    activities: list[ActivityIn] = []


class DeliverableIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    classification: Classification = Classification.RECOMMENDED
    stage_key: str | None = None  # matches StageIn.key (or a stage index as a string)
    template_id: uuid.UUID | None = None


class MethodologyMeta(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: MethodologyKind | None = None
    purpose: str | None = None
    when_to_use: str | None = None
    prerequisites: str | None = None
    tools: str | None = None
    dependencies: str | None = None
    common_risks: str | None = None
    completion_criteria: str | None = None
    limitations: str | None = None
    change_note: str | None = Field(default=None, max_length=2000)


class MethodologyCreate(MethodologyMeta):
    name: str = Field(min_length=1, max_length=200)
    kind: MethodologyKind = MethodologyKind.METHODOLOGY
    stages: list[StageIn] = []
    deliverables: list[DeliverableIn] = []


class StructureIn(BaseModel):
    stages: list[StageIn]
    deliverables: list[DeliverableIn] = []
    change_note: str | None = Field(default=None, max_length=2000)


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    position: int
    title: str
    instructions: str | None
    expected_output: str | None


class StageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    position: int
    name: str
    description: str | None
    validation_criteria: str | None
    activities: list[ActivityOut]


class DeliverableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    stage_id: uuid.UUID | None
    position: int
    name: str
    description: str | None
    classification: Classification
    template_id: uuid.UUID | None


class AdoptionRef(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    methodology_version: int
    adopted_at: datetime


class MethodologySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    slug: str
    name: str
    kind: MethodologyKind
    status: MethodologyStatus
    purpose: str | None
    when_to_use: str | None
    version: int
    origin_project_id: uuid.UUID | None
    origin_project_name: str | None = None
    archived_at: datetime | None
    updated_at: datetime
    stage_count: int = 0
    activity_count: int = 0
    deliverable_count: int = 0
    adoption_count: int = 0


class MethodologyDetail(MethodologySummary):
    prerequisites: str | None
    tools: str | None
    dependencies: str | None
    common_risks: str | None
    completion_criteria: str | None
    limitations: str | None
    stages: list[StageOut]
    deliverables: list[DeliverableOut]
    adoptions: list[AdoptionRef]


class MethodologyVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int
    snapshot: dict
    change_note: str | None
    created_at: datetime


class PublishIn(BaseModel):
    change_note: str | None = Field(default=None, max_length=2000)


class DuplicateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    origin_project_id: uuid.UUID | None = None


class FromProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: MethodologyKind = MethodologyKind.PLAYBOOK


class AdoptIn(BaseModel):
    methodology_id: uuid.UUID
    stage_ids: list[uuid.UUID] | None = None  # None = all stages
    create_milestones: bool = True
    create_tasks: bool = True
    start_date: date | None = None  # milestones spaced a week apart from here, if given
    notes: str | None = None


class ProjectDeliverableOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    definition_id: uuid.UUID | None
    name: str
    classification: Classification
    status: DeliverableStatus
    document_id: uuid.UUID | None
    milestone_id: uuid.UUID | None
    notes: str | None


class AdoptionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    methodology_id: uuid.UUID
    methodology_name: str
    methodology_version: int
    current_version: int
    stage_ids: list[uuid.UUID]
    notes: str | None
    adopted_at: datetime
    deliverables: list[ProjectDeliverableOut]
    milestones_created: int = 0
    tasks_created: int = 0


class ProjectDeliverableUpdate(BaseModel):
    status: DeliverableStatus | None = None
    classification: Classification | None = None
    document_id: uuid.UUID | None = None
    notes: str | None = None
