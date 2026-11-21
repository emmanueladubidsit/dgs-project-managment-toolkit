# ADR 0002 — Planning on the task record; weighted, explained progress

- **Status:** Accepted · 21 November 2026

## Context

The brief requires all views to use the same records, progress that is not a naive task count,
transparent calculations, and no automatic completion.

## Decision

1. **Scheduling lives on `Task.scheduled_date`.** Day/week/month notes (`plan_notes`) hold only
   objectives, notes and available hours. There is no separate “plan item” table to drift out of sync.
2. **Progress = Σ(weight × value) / Σ(weight)** over counted tasks, where weight is the explicit
   `weight`, else `estimate_hours`, else 1; value is 100 for Completed, otherwise `progress`;
   Cancelled tasks are excluded; project progress counts top-level tasks only. Every result carries
   a plain-English `explanation`.
3. **No automatic completion** of parents, milestones or projects. Completing a task sets its
   progress to 100%; reopening keeps the recorded progress but clears `completed_at`.
4. **Capacity is never assumed**: over-capacity is reported only against hours the user entered.

## Consequences

- Board, list, planner, dashboard and reports agree by construction.
- Weights make large tasks count more without forcing estimates on everything.
- Users stay in control of what “done” means; the UI nudges (e.g. “all subtasks completed”) but
  never decides.
