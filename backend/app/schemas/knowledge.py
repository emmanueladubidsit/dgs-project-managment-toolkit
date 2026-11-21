import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.knowledge import KnowledgeCategory, LinkRole, RelationKind, Verification


def _clean_tags(v: list[str]) -> list[str]:
    out: list[str] = []
    for t in v:
        t = t.strip()[:60]
        if t and t not in out:
            out.append(t)
    return out


class KnowledgeIn(BaseModel):
    category: KnowledgeCategory
    title: str = Field(min_length=1, max_length=300)
    summary: str | None = None
    content: str | None = None
    fields: dict[str, str | None] = {}
    verification: Verification = Verification.RESEARCH_UNIMPLEMENTED
    tags: list[str] = []
    sources: str | None = None
    limitations: str | None = None
    reuse_notes: str | None = None
    origin_project_id: uuid.UUID | None = None

    @field_validator("tags")
    @classmethod
    def _t(cls, v: list[str]) -> list[str]:
        return _clean_tags(v)


class KnowledgeUpdate(BaseModel):
    category: KnowledgeCategory | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    summary: str | None = None
    content: str | None = None
    fields: dict[str, str | None] | None = None
    verification: Verification | None = None
    tags: list[str] | None = None
    sources: str | None = None
    limitations: str | None = None
    reuse_notes: str | None = None
    change_note: str | None = Field(default=None, max_length=2000)

    @field_validator("tags")
    @classmethod
    def _t(cls, v):
        return _clean_tags(v) if v is not None else v


class ProjectLinkIn(BaseModel):
    project_id: uuid.UUID
    role: LinkRole = LinkRole.RELATED
    note: str | None = None


class TaskLinkIn(BaseModel):
    task_id: uuid.UUID


class RelationIn(BaseModel):
    to_id: uuid.UUID
    kind: RelationKind = RelationKind.RELATED


class ProjectLinkOut(BaseModel):
    project_id: uuid.UUID
    project_name: str
    role: LinkRole
    note: str | None
    created_at: datetime


class TaskLinkOut(BaseModel):
    task_id: uuid.UUID
    task_title: str
    project_name: str


class RelationOut(BaseModel):
    id: uuid.UUID
    kind: RelationKind
    direction: str  # "outgoing" (this → other) or "incoming"
    other_id: uuid.UUID
    other_title: str
    other_category: KnowledgeCategory
    other_verification: Verification


class KnowledgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    category: KnowledgeCategory
    title: str
    summary: str | None
    content: str | None
    fields: dict
    verification: Verification
    tags: list[str]
    sources: str | None
    limitations: str | None
    reuse_notes: str | None
    version: int
    source_work_log_id: uuid.UUID | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    projects: list[ProjectLinkOut] = []


class KnowledgeDetail(KnowledgeOut):
    tasks: list[TaskLinkOut]
    relations: list[RelationOut]


class KnowledgeVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int
    snapshot: dict
    change_note: str | None
    created_at: datetime


class TemplateField(BaseModel):
    key: str
    label: str
    hint: str


class CategoryTemplate(BaseModel):
    category: KnowledgeCategory
    label: str
    fields: list[TemplateField]


class SearchHit(BaseModel):
    type: str
    id: uuid.UUID
    title: str
    snippet: str | None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    meta: str | None = None
