# Product requirements

The full product brief is [`prompt.md`](../prompt.md). This document summarises the vision, the
MVP scope and the **verified** status of each acceptance criterion.

## Vision

A personal, local-first workspace that takes projects from ideation to maintenance and makes each
project easier than the last: *every discussion can become knowledge, every piece of knowledge an
artefact, every artefact can inform a task, every task contributes to a milestone, every
milestone to a project outcome.*

Principles: real working software over mock-ups; deterministic core that needs no AI; AI only as
reviewable suggestions; never invent progress, hours, commitments or facts; British English.

## Users

A single user (the owner) managing several engineering and research projects day to day.
Multi-user support is a future consideration, not an MVP requirement.

## MVP acceptance criteria — status

✅ verified by automated tests (and manual checks where noted) · ⏳ not yet built

### Project management
- ✅ Create a project · ✅ edit and archive · ✅ data persists after restarting the application
  (API and database restarted, record intact) · ✅ view status and progress.

### Task management
- ✅ Create tasks and subtasks · ✅ associate with projects, workstreams and milestones · ✅ set
  priority, status, dates and estimates · ✅ update progress · ✅ move through the Kanban board ·
  ✅ filter and search · ✅ record task updates (comments) · ✅ identify blocked and overdue tasks ·
  ✅ view task history · ✅ changes persist.

### Planning
- ✅ Plan tasks for a day and week · ✅ view upcoming deadlines · ✅ reschedule unfinished tasks
  (individually or carry-forward) · ✅ track milestones · ✅ see progress against objectives.

### Reporting
- ✅ Generate a daily report · ✅ generate a weekly report · ✅ reports reflect stored data only ·
  ✅ edit and copy reports (also download and save).

### Knowledge
- ✅ Create research and knowledge records · ✅ categorise them · ✅ associate with projects ·
  ✅ search previously captured knowledge (list search and global search) · ✅ create a reusable
  guide or template (and methodologies/playbooks, including from a past project).

### General usability
- ✅ Application starts · ✅ persistent database · ✅ frontend communicates with backend ·
  ✅ errors handled with clear messages · ✅ useful empty states · ✅ navigation works ·
  ✅ usable without an AI key · ✅ tested.

## Assumptions made

- Weeks start on Monday (UK convention).
- “Progress against objectives” is shown as weighted project and milestone progress next to the
  written objectives; objectives are free text until a structured objectives model is needed.
- Decisions and research are captured as typed work logs until the knowledge module exists.
- Default ports 3010/8010/5433 avoid clashes with other local projects.
