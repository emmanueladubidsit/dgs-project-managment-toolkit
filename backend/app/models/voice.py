"""Voice notes, transcripts and reviewable suggestions (Modules E and J)."""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin
from app.models.enums import str_enum


class SuggestionKind(StrEnum):
    TASK = "task"
    TASK_UPDATE = "task_update"  # change an existing task (e.g. mark completed)
    BLOCKER = "blocker"
    DECISION = "decision"
    PROGRESS = "progress"
    MILESTONE = "milestone"  # create or update a milestone (from a project tracker)


class SuggestionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class VoiceNote(IdMixin, TimestampMixin, Base):
    """A recording or a piece of pasted/typed text, plus its transcript and edits."""

    __tablename__ = "voice_notes"

    title: Mapped[str] = mapped_column(String(300))
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[str] = mapped_column(String(20), default="recording")  # recording | text
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    # Present only while the audio is retained (see Settings.voice_retention).
    audio_path: Mapped[str | None] = mapped_column(String(500))
    audio_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transcript_raw: Mapped[str | None] = mapped_column(Text)
    transcript_edited: Mapped[str | None] = mapped_column(Text)
    transcription_provider: Mapped[str | None] = mapped_column(String(60))
    language: Mapped[str] = mapped_column(String(10), default="en-GB")

    project = relationship("Project", lazy="joined")


class Suggestion(IdMixin, TimestampMixin, Base):
    """A proposed change awaiting review. Nothing enters the backlog until approved."""

    __tablename__ = "suggestions"

    kind: Mapped[SuggestionKind] = mapped_column(str_enum(SuggestionKind, "suggestion_kind"))
    status: Mapped[SuggestionStatus] = mapped_column(
        str_enum(SuggestionStatus, "suggestion_status"),
        default=SuggestionStatus.PENDING,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(30))  # voice_note | text
    source_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    generator: Mapped[str] = mapped_column(String(60))  # e.g. "rules" or an AI provider name
    payload: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # e.g. {"title": ..., "priority": ...}
    evidence: Mapped[str | None] = mapped_column(Text)  # the source sentence it came from
    duplicate_of_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL")
    )
    created_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL")
    )
    created_work_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_logs.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", lazy="joined")
