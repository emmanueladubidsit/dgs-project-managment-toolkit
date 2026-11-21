# ADR 0004 — One knowledge table with category templates

- **Status:** Accepted · 21 November 2026

## Context

The brief lists 14 knowledge categories (research, troubleshooting, decisions, lessons learned…)
and separate entities such as ResearchRecord, KnowledgeItem and DecisionRecord, each with its own
fields. Knowledge must be searchable across categories, versioned, verifiable and reusable.

## Decision

- A single `knowledge_items` table. Category-specific structure lives in a validated JSONB
  `fields` column. The templates (`backend/app/services/knowledge_templates.py`) are the single
  source of truth; the API serves them to the UI, which renders the forms from them. Unknown keys
  are rejected.
- Every substantive edit snapshots the previous state into `knowledge_versions` and bumps the
  version. Restoring creates a *new* version, so history is never rewritten.
- Provenance and reuse are links to projects with a role (`origin` / `reused` / `related`);
  only one origin is allowed and it cannot be changed. Decisions link to evidence through
  `knowledge_relations` (`evidence_for`, `supersedes`, `related`). Superseding marks the older
  item *Outdated*.
- Verification is an explicit field that defaults to *Research — not yet applied*. Nothing is
  marked verified automatically, and AI suggestions carry a distinct status and on-page warning.

## Consequences

- One search and one list cover every kind of knowledge; adding a category means adding a
  template entry, not a migration.
- Field-level constraints are enforced in the application rather than by database columns.
- Recorded decisions and research (work logs) can be promoted to a draft knowledge item with
  provenance kept (`POST /knowledge/from-work-log/{id}`).
