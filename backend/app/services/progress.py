"""Transparent, weighted progress calculation.

Rules (documented in docs/ARCHITECTURE.md):
- Only the tasks passed in are counted (callers pass top-level, non-archived tasks, so
  subtasks are not double-counted — a parent's own progress field represents it).
- Cancelled tasks are excluded.
- A task's weight is its explicit `weight` if set, otherwise its `estimate_hours`,
  otherwise 1. Big or important tasks therefore count for more than small ones.
- A task's contribution is 100% if Completed, otherwise its recorded progress %.
- Nothing is ever marked complete automatically as a result of this calculation.
"""

from collections.abc import Iterable
from decimal import Decimal

from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.project import ProgressBreakdown


def task_weight(task: Task) -> float:
    if task.weight:
        return float(task.weight)
    if task.estimate_hours and task.estimate_hours > Decimal(0):
        return float(task.estimate_hours)
    return 1.0


def task_value(task: Task) -> float:
    return 100.0 if task.status == TaskStatus.COMPLETED else float(task.progress or 0)


def weighted_progress(tasks: Iterable[Task]) -> ProgressBreakdown:
    tasks = list(tasks)
    counted = [t for t in tasks if t.status != TaskStatus.CANCELLED]
    excluded = len(tasks) - len(counted)
    completed = sum(1 for t in counted if t.status == TaskStatus.COMPLETED)

    if not counted:
        return ProgressBreakdown(
            percent=0.0,
            method="none",
            explanation="No active tasks yet, so progress cannot be calculated.",
            tasks_counted=0,
            tasks_completed=0,
            tasks_excluded=excluded,
            total_weight=0.0,
        )

    weights = [task_weight(t) for t in counted]
    total_weight = sum(weights)
    percent = sum(w * task_value(t) for w, t in zip(weights, counted, strict=True)) / total_weight
    uniform = len(set(weights)) == 1
    method = "equal" if uniform else "weighted"
    basis = (
        "each task counts equally"
        if uniform
        else "tasks are weighted by their explicit weight, else estimated hours, else 1"
    )
    explanation = (
        f"{percent:.0f}% across {len(counted)} task(s): {basis}. "
        f"Completed tasks count as 100%; others use their recorded progress. "
        f"{completed} of {len(counted)} completed"
        + (f"; {excluded} cancelled task(s) excluded." if excluded else ".")
    )
    return ProgressBreakdown(
        percent=round(percent, 1),
        method=method,
        explanation=explanation,
        tasks_counted=len(counted),
        tasks_completed=completed,
        tasks_excluded=excluded,
        total_weight=round(total_weight, 2),
    )
