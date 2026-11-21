"""A project's connected codebase folder, and activity from git and Claude Code."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, IdMixin, TimestampMixin


class ProjectConnection(IdMixin, TimestampMixin, Base):
    """One codebase folder per project, read only. Git is used when the folder is a repository."""

    __tablename__ = "project_connections"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True
    )
    path: Mapped[str] = mapped_column(String(1000), index=True)
    is_git: Mapped[bool] = mapped_column(Boolean, default=False)
    accept_claude: Mapped[bool] = mapped_column(Boolean, default=True)  # hook/MCP reports
    auto_sync: Mapped[bool] = mapped_column(Boolean, default=True)
    branch: Mapped[str | None] = mapped_column(String(200))
    head: Mapped[str | None] = mapped_column(String(64))
    uncommitted_changes: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    project = relationship("Project", lazy="joined")


class CodeEvent(IdMixin, Base):
    """A commit, a Claude Code session summary or a completed Claude task. Metadata only:
    no source code, prompts, commands or author names are stored."""

    __tablename__ = "code_events"
    __table_args__ = (UniqueConstraint("connection_id", "kind", "ref", name="uq_code_event_ref"),)

    connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project_connections.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))  # commit | claude_session | claude_task | files
    ref: Mapped[str] = mapped_column(String(200))  # commit hash, session id, task id…
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)  # files, branch, counts…
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone()
    )
