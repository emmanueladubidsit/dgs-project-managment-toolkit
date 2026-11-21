"""Reusable methodologies, playbooks and starter kits (Module G), and their adoption by projects."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.models.enums import str_enum


class MethodologyKind(StrEnum):
    METHODOLOGY = "methodology"
    PLAYBOOK = "playbook"
    STARTER_KIT = "starter_kit"


class MethodologyStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class Classification(StrEnum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    NOT_APPLICABLE = "not_applicable"


class DeliverableStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    NOT_APPLICABLE = "not_applicable"


class Methodology(IdMixin, TimestampMixin, Base):
    __tablename__ = "methodologies"

    slug: Mapped[str] = mapped_column(String(120), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[MethodologyKind] = mapped_column(
        str_enum(MethodologyKind, "methodology_kind"), default=MethodologyKind.METHODOLOGY
    )
    status: Mapped[MethodologyStatus] = mapped_column(
        str_enum(MethodologyStatus, "methodology_status"), default=MethodologyStatus.DRAFT
    )
    purpose: Mapped[str | None] = mapped_column(Text)
    when_to_use: Mapped[str | None] = mapped_column(Text)
    prerequisites: Mapped[str | None] = mapped_column(Text)
    tools: Mapped[str | None] = mapped_column(Text)
    dependencies: Mapped[str | None] = mapped_column(Text)
    common_risks: Mapped[str | None] = mapped_column(Text)
    completion_criteria: Mapped[str | None] = mapped_column(Text)
    limitations: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # Provenance: the project this methodology was derived from, if any.
    origin_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL")
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    stages: Mapped[list["MethodologyStage"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="MethodologyStage.position",
    )
    deliverables: Mapped[list["DeliverableDefinition"]] = relationship(
        back_populates="methodology",
        cascade="all, delete-orphan",
        order_by="DeliverableDefinition.position",
    )


class MethodologyStage(IdMixin, Base):
    __tablename__ = "methodology_stages"

    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    validation_criteria: Mapped[str | None] = mapped_column(Text)

    methodology: Mapped[Methodology] = relationship(back_populates="stages")
    activities: Mapped[list["MethodologyActivity"]] = relationship(
        back_populates="stage",
        cascade="all, delete-orphan",
        order_by="MethodologyActivity.position",
    )


class MethodologyActivity(IdMixin, Base):
    __tablename__ = "methodology_activities"

    stage_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodology_stages.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(300))
    instructions: Mapped[str | None] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)

    stage: Mapped[MethodologyStage] = relationship(back_populates="activities")


class DeliverableDefinition(IdMixin, Base):
    __tablename__ = "deliverable_definitions"

    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id", ondelete="CASCADE"), index=True
    )
    stage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("methodology_stages.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[Classification] = mapped_column(
        str_enum(Classification, "deliverable_classification"), default=Classification.RECOMMENDED
    )
    # Optional template in the knowledge library.
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_items.id", ondelete="SET NULL")
    )

    methodology: Mapped[Methodology] = relationship(back_populates="deliverables")
    stage: Mapped["MethodologyStage | None"] = relationship()


class MethodologyVersion(IdMixin, Base):
    """Full snapshot of a methodology, taken whenever its version number is bumped."""

    __tablename__ = "methodology_versions"
    __table_args__ = (UniqueConstraint("methodology_id", "version", name="uq_methodology_version"),)

    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    change_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )


class ProjectMethodology(IdMixin, Base):
    """A project's adoption of a methodology (whole or selected stages)."""

    __tablename__ = "project_methodologies"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    methodology_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("methodologies.id", ondelete="CASCADE"), index=True
    )
    methodology_version: Mapped[int] = mapped_column(Integer)
    stage_ids: Mapped[list] = mapped_column(JSONB, default=list)  # stages adopted
    notes: Mapped[str | None] = mapped_column(Text)
    adopted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )

    methodology: Mapped[Methodology] = relationship(lazy="joined")
    project = relationship("Project", lazy="joined")
    deliverables: Mapped[list["ProjectDeliverable"]] = relationship(
        back_populates="adoption", cascade="all, delete-orphan"
    )


class ProjectDeliverable(IdMixin, TimestampMixin, Base):
    """A methodology deliverable as tracked in one project (classification can be overridden)."""

    __tablename__ = "project_deliverables"

    adoption_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_methodologies.id", ondelete="CASCADE"), index=True
    )
    definition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("deliverable_definitions.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200))
    classification: Mapped[Classification] = mapped_column(
        str_enum(Classification, "project_deliverable_classification")
    )
    status: Mapped[DeliverableStatus] = mapped_column(
        str_enum(DeliverableStatus, "project_deliverable_status"), default=DeliverableStatus.PENDING
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_documents.id", ondelete="SET NULL")
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)

    adoption: Mapped[ProjectMethodology] = relationship(back_populates="deliverables")
