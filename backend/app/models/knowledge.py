"""Knowledge, research and reusable guidance (Module F).

One table holds every knowledge category; category-specific structure (research questions,
troubleshooting steps, decision context…) lives in the validated JSONB `fields` column — see
ADR 0004. Every edit snapshots a version; provenance and reuse are tracked through project links.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.models.enums import str_enum


class KnowledgeCategory(StrEnum):
    RESEARCH = "research"
    TROUBLESHOOTING = "troubleshooting"
    RUNBOOK = "runbook"
    PLAYBOOK = "playbook"
    TECHNICAL_STANDARD = "technical_standard"
    DESIGN_STANDARD = "design_standard"
    ARCHITECTURE_PATTERN = "architecture_pattern"
    DECISION = "decision"
    LESSON_LEARNED = "lesson_learned"
    TEMPLATE = "template"
    REUSABLE_COMPONENT = "reusable_component"
    SETUP_GUIDE = "setup_guide"
    CHECKLIST = "checklist"
    PROJECT_DOCUMENTATION = "project_documentation"


class Verification(StrEnum):
    VERIFIED_TESTED = "verified_tested"
    VERIFIED_DOCS = "verified_docs"
    APPLIED_IN_PROJECT = "applied_in_project"
    RESEARCH_UNIMPLEMENTED = "research_unimplemented"
    AI_SUGGESTION = "ai_suggestion"
    OUTDATED = "outdated"


class LinkRole(StrEnum):
    ORIGIN = "origin"  # the project this knowledge came from
    REUSED = "reused"  # applied again in another project
    RELATED = "related"


class RelationKind(StrEnum):
    EVIDENCE_FOR = "evidence_for"
    SUPERSEDES = "supersedes"
    RELATED = "related"


class KnowledgeItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_items"

    category: Mapped[KnowledgeCategory] = mapped_column(
        str_enum(KnowledgeCategory, "knowledge_category"), index=True
    )
    title: Mapped[str] = mapped_column(String(300), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)  # free-form Markdown body
    fields: Mapped[dict] = mapped_column(JSONB, default=dict)  # category-specific structure
    verification: Mapped[Verification] = mapped_column(
        str_enum(Verification, "knowledge_verification"),
        default=Verification.RESEARCH_UNIMPLEMENTED,
        index=True,
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list)
    sources: Mapped[str | None] = mapped_column(Text)
    limitations: Mapped[str | None] = mapped_column(Text)
    reuse_notes: Mapped[str | None] = mapped_column(Text)  # what to adapt before reusing
    version: Mapped[int] = mapped_column(Integer, default=1)
    source_work_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_logs.id", ondelete="SET NULL")
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project_links: Mapped[list["KnowledgeProjectLink"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class KnowledgeVersion(IdMixin, Base):
    """Snapshot taken before each change, so history and earlier wording are preserved."""

    __tablename__ = "knowledge_versions"
    __table_args__ = (UniqueConstraint("item_id", "version", name="uq_knowledge_version"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    change_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )


class KnowledgeProjectLink(IdMixin, Base):
    __tablename__ = "knowledge_project_links"
    __table_args__ = (UniqueConstraint("item_id", "project_id", name="uq_knowledge_project"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[LinkRole] = mapped_column(str_enum(LinkRole, "knowledge_link_role"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )

    item: Mapped[KnowledgeItem] = relationship(back_populates="project_links")
    project = relationship("Project", lazy="joined")


class KnowledgeTaskLink(IdMixin, Base):
    __tablename__ = "knowledge_task_links"
    __table_args__ = (UniqueConstraint("item_id", "task_id", name="uq_knowledge_task"),)

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )
    task = relationship("Task", lazy="joined")


class KnowledgeRelation(IdMixin, Base):
    """Directed link between knowledge items, e.g. research `evidence_for` a decision."""

    __tablename__ = "knowledge_relations"
    __table_args__ = (
        UniqueConstraint("from_id", "to_id", "kind", name="uq_knowledge_relation"),
        CheckConstraint("from_id <> to_id", name="not_self"),
    )

    from_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), index=True
    )
    to_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[RelationKind] = mapped_column(str_enum(RelationKind, "knowledge_relation"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )
