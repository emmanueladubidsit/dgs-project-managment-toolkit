"""System settings and AI usage records."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, IdMixin, TimestampMixin


class SystemSetting(TimestampMixin, Base):
    """Non-secret configuration editable from Administration. Secrets stay in backend/.env."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class AIInteraction(IdMixin, Base):
    """Metadata about each AI call (never the prompt or the answer), for transparency."""

    __tablename__ = "ai_interactions"

    feature: Mapped[str] = mapped_column(String(60), index=True)
    provider: Mapped[str] = mapped_column(String(60))
    model: Mapped[str | None] = mapped_column(String(120))
    prompt_chars: Mapped[int] = mapped_column(Integer, default=0)
    response_chars: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now().astimezone(), index=True
    )
