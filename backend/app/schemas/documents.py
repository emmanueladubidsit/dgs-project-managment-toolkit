import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.documents import DocumentCategory, DocumentStatus


def check_url(v: str | None) -> str | None:
    """Only web links: blocks javascript:, file: and other schemes."""
    if v and not v.strip().lower().startswith(("http://", "https://")):
        raise ValueError("Links must start with http:// or https://.")
    return v.strip() if v else v


class RootIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    path: str = Field(min_length=1, max_length=1000)
    project_id: uuid.UUID | None = None


class RootOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    path: str
    project_id: uuid.UUID | None
    project_name: str | None = None
    last_scanned_at: datetime | None
    document_count: int = 0
    available: bool = True


class ScannedFile(BaseModel):
    relative_path: str
    size_bytes: int
    modified_at: datetime
    suggested_category: DocumentCategory
    document_id: uuid.UUID | None = None


class ScanResult(BaseModel):
    root_id: uuid.UUID
    files: list[ScannedFile]
    truncated: bool
    skipped_note: str


class RegisterIn(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    category: DocumentCategory | None = None  # None = use the suggested category per file


class DocumentIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    category: DocumentCategory = DocumentCategory.OTHER
    status: DocumentStatus = DocumentStatus.DRAFT
    description: str | None = None
    project_id: uuid.UUID | None = None
    url: str | None = Field(default=None, max_length=1000)
    content: str | None = None
    tags: list[str] = []

    @field_validator("url")
    @classmethod
    def _url(cls, v: str | None) -> str | None:
        return check_url(v)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    category: DocumentCategory | None = None
    status: DocumentStatus | None = None
    description: str | None = None
    project_id: uuid.UUID | None = None
    url: str | None = Field(default=None, max_length=1000)
    content: str | None = None
    tags: list[str] | None = None

    @field_validator("url")
    @classmethod
    def _url(cls, v: str | None) -> str | None:
        return check_url(v)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    category: DocumentCategory
    status: DocumentStatus
    description: str | None
    project_id: uuid.UUID | None
    project_name: str | None = None
    root_id: uuid.UUID | None
    root_name: str | None = None
    relative_path: str | None
    url: str | None
    content: str | None
    tags: list[str]
    size_bytes: int | None
    file_modified_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    source: str  # "file" | "link" | "note"
    file_available: bool | None = None
    tasks: list[dict] = []


class TaskLink(BaseModel):
    task_id: uuid.UUID


class PreviewOut(BaseModel):
    document_id: uuid.UUID
    text: str
    truncated: bool = False
