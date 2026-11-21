"""Domain enumerations. Stored as strings with CHECK constraints (not native PG enums)
so values can be extended with a simple migration."""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Priority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MilestoneStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    MISSED = "missed"
    CANCELLED = "cancelled"


class WorkLogKind(StrEnum):
    PROGRESS = "progress"
    DECISION = "decision"
    BLOCKER = "blocker"
    RESEARCH = "research"
    UNPLANNED = "unplanned"
    NOTE = "note"


class PlanPeriod(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ReportKind(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    PROJECT = "project"


def str_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )
