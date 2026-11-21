"""Project documents and registered directories (Module H).

Files stay where they are: the workspace indexes and links them, and reads text previews
through validated paths. It never moves, deletes, overwrites or modifies a file.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.models.enums import str_enum


class DocumentCategory(StrEnum):
    BRIEF = "brief"
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    ADR = "adr"
    DESIGN = "design"
    DIAGRAM = "diagram"
    RESEARCH = "research"
    REPORT = "report"
    PROTOTYPE = "prototype"
    SPECIFICATION = "specification"
    TESTING = "testing"
    RELEASE_NOTES = "release_notes"
    MEETING_NOTES = "meeting_notes"
    PRESENTATION = "presentation"
    OTHER = "other"


class DocumentStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"
    SUPERSEDED = "superseded"


class DocumentRoot(IdMixin, TimestampMixin, Base):
    """A directory the user has explicitly registered for read-only indexing."""

    __tablename__ = "document_roots"

    name: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(String(1000), unique=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", lazy="joined")


class ProjectDocument(IdMixin, TimestampMixin, Base):
    """A document record: a file inside a registered root, an external URL, or in-app text."""

    __tablename__ = "project_documents"
    __table_args__ = (UniqueConstraint("root_id", "relative_path", name="uq_document_root_path"),)

    title: Mapped[str] = mapped_column(String(300), index=True)
    category: Mapped[DocumentCategory] = mapped_column(
        str_enum(DocumentCategory, "document_category"), default=DocumentCategory.OTHER, index=True
    )
    status: Mapped[DocumentStatus] = mapped_column(
        str_enum(DocumentStatus, "document_status"), default=DocumentStatus.DRAFT
    )
    description: Mapped[str | None] = mapped_column(Text)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    root_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_roots.id", ondelete="SET NULL"), index=True
    )
    relative_path: Mapped[str | None] = mapped_column(String(1000))
    url: Mapped[str | None] = mapped_column(String(1000))
    content: Mapped[str | None] = mapped_column(Text)  # basic text for in-app documents
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    file_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", lazy="joined")
    root = relationship("DocumentRoot", lazy="joined")


class DocumentTaskLink(IdMixin, Base):
    __tablename__ = "document_task_links"
    __table_args__ = (UniqueConstraint("document_id", "task_id", name="uq_document_task"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_documents.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )
    task = relationship("Task", lazy="joined")
