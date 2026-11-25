# ADR 0010 — Project tracker import, projects folder and discovery

- **Status:** Accepted · 25 November 2026 · amends ADR 0009 (local progress files)

## Context

Claude Code keeps a daily progress report and plan in each project
(`docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md`): work done per working day with
evidence, milestone criteria marked **Verified / In progress / Not started**, and the proposed plan
for coming weeks (`### Week 3 (30 Nov to 4 Dec), M3: …`). The user wants this in every project, with
working days Monday to Friday and weekend work counted on the next Monday. ADR 0009's reader only
knew task IDs and checklists, so this work never reached the right tasks, milestones or days.
Projects also lived in scattered folders, mixed with non-technical work.

## Decision

1. **One tracker format, read only.** `services/tracker.py` reads the newest tracker (by the date
   in its name) and recognises: `| Day | What was done | Evidence |` tables, `**Week N milestone
   (…):**` status bullets, `### Week N (…), Mk: title` plans with `| Day | Task |` or
   `| When | Tasks | Done when |` tables, and `**Mk success criteria (Day):** a; b`. Unknown sections are
   ignored and reported as warnings. Dates are resolved from the day cell (e.g. `Wed 18`) and the
   heading's range, including across a year end.
2. **Working days.** Saturday and Sunday map to the following Monday (`working_day`). Weekend work
   is shown as "done Sat 21 Nov, counted on Mon 23 Nov"; a milestone's due date ignores carried work.
3. **Everything is a suggestion (ADR 0002 unchanged).** Each refresh proposes milestones, new tasks,
   status changes, plan scheduling and one work-log entry per working day. The user can edit each
   item (title, status, progress, milestone, workstream, planned day, due date) and approve one at a
   time, per day/section, or all at once (`POST /suggestions/approve-batch`; milestones first so
   tasks can join them). Completed work is dated to its working day.
4. **Matching is conservative.** A task is the same work only when the tracker names its ID or the
   title is near-identical. An ID next to "logged/opened/found…" is a new record, not progress on
   that issue. Looser overlaps become new-task suggestions flagged "possibly the same as …". Status
   only moves forward. Planned work on an open task proposes its day (or a reschedule) and
   milestone. `tracker_entries` remembers what was proposed, so rejected items are not proposed
   again unless the tracker changes their status.
5. **Projects folder.** A recommended root (`PROJECTS_ROOT`, overridable in Administration and
   stored as the `projects` system setting) holds technical projects. **Discover projects** scans
   it (two levels; folders with `.git`, `CLAUDE.md`, `.claude`, a tracker, `package.json` or
   `pyproject.toml`; no symlinks; dependency folders skipped) and adds a project with a read-only
   connection.
6. **The only write.** **Start a new project** creates `<root>/<name>/` with a starter tracker and
   a `CLAUDE.md` explaining the format. Files are created with exclusive create (never
   overwritten), and a non-empty folder is refused. Existing projects are never edited; Administration
   shows the instructions to copy.

## Consequences

- Progress Claude records daily lands on the right tasks, milestones and days after one review.
- Depends on the tracker keeping the documented structure; warnings make drift visible.
- The background sync also refreshes trackers, so new items appear without pressing Refresh.
- The workspace now writes to disk in exactly one, user-initiated place.
