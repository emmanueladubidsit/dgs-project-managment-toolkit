# User guide

Open **http://localhost:3010** after starting the app (see the README). The dot in the header
shows whether the server is connected.

## 1. Set up a project

1. **Projects → New project.** Only the name is required. Choose a lifecycle stage, priority,
   dates and the workstreams you actually need (you can change them later).
2. Use **“Add problem statement, scope, users, risks and more…”** to capture context. Leave
   unknowns blank; the Overview shows them as “Not yet defined” so gaps stay visible.

## 2. Break the work down

Inside a project:

- **Workstreams tab** — add, rename or remove workstreams (removing one keeps its tasks).
- **Milestones tab** — add milestones with due dates and deliverables. Warnings flag missing
  deliverables, missing tasks, tasks without acceptance criteria and overdue milestones. A
  milestone is only *Achieved* when you set it.
- **New task** — link it to a workstream and milestone; add an estimate, acceptance criteria and
  deliverables. Open any task to add **subtasks**, **dependencies** (“waits for”) and **updates**.

**Status and progress are separate.** Set status (To Do, In Progress, Blocked, In Review,
Completed, Cancelled) and progress % independently. Completing a task sets it to 100%; completing
all subtasks never completes the parent for you.

**How progress is calculated:** hover or focus any progress bar. Tasks are weighted by their
explicit *weight*, otherwise their estimated hours, otherwise equally. Cancelled tasks are left out.

## 3. Work the tasks

- **Board** — drag cards between columns, or use a card's **⋯** menu (keyboard friendly).
- **Backlog / My Tasks** — search, filter by status, priority, overdue or blocked; sort; select
  several tasks to change status or priority, or plan them for today, in one go.
- Click any task title to open its panel: quick status/priority/progress/planned-day controls,
  subtasks, dependencies, updates and full history. Archive keeps a task but hides it; Delete is
  permanent and asks for confirmation.

## 4. Plan your time

**Planner → Day**: tasks planned for the day, tasks **carried over** from earlier days (move one,
or “Move all”), tasks due but not planned, completed work, blockers and updates. Record the
day's objectives and **available hours** — capacity is only checked when you enter hours.

**Week**: drag tasks between days or from *Unscheduled*; see planned hours per day, deadlines,
upcoming milestones, and planned-versus-completed counts. **Month**: weekly planned-versus-completed,
milestones and deadlines, monthly objectives.

**Plan check** (project tab): missing acceptance criteria, estimates and deliverables; tasks due
before the work they depend on; bottlenecks; work past the target date; over-capacity days.

## 5. Record what happened

**Add daily update** (dashboard, project header or planner): choose *Progress update*,
*Decision*, *Blocker*, *Research*, *Unplanned work* or *Note*, optionally link a project and task,
and record hours. Updates appear on the project's **Decisions & updates** tab and in reports.

## 6. Report

**Reports** (or a project's Reports tab): choose daily, weekly or project, a date, an optional
project and a stakeholder or technical format, then **Generate**. Edit the Markdown, then **Copy**,
**Download .md** or **Save**. Reports contain only recorded data; empty sections say “None recorded”.

## 7. Keep and reuse knowledge

**Knowledge & Research → New item.** Choose a category (research, troubleshooting guide, decision,
runbook, lesson learned, template…) to get its structured fields. Set the **verification status**
honestly — items start as “Research — not yet applied”. Every save keeps the previous version;
restore any version from the history. On an item you can record its **origin project**, mark where
it was **reused**, link tasks, and link other items as **evidence for** a decision or as
**superseded** (the older item is then marked Outdated). On a project's **Decisions & updates**
tab, **Save to knowledge** turns a recorded decision or research note into a draft item.

## 8. Methodologies & playbooks

Browse the library (13 starter methodologies, including *Assessing an existing codebase*). Open
one to see its stages, activities, expected outputs and deliverables. **Adopt into a project** —
all stages or only some — to create a milestone per stage and a task per activity (existing tasks
with the same title are skipped). Track deliverables on the project's **Methodology** tab. Edit
**Details** or **Stages** to change a methodology (each change is versioned), **Publish** it when
ready, or **Duplicate** it to adapt it. When a project goes well, use **Save as reusable playbook**
(project Methodology tab) or **Create from a project** to turn its plan into a draft — then remove
anything project-specific or confidential before publishing.

## 9. Documents & artefacts

**Folders tab:** register a project folder by its full path, then **Scan and choose files** and
index the ones you want. The workspace only reads files: it never moves, edits or deletes them,
and it never lists or opens secret files such as `.env` or keys. **Documents tab:** filter and
search; add links to documents elsewhere or short notes; open a document to change its category,
status or project, preview text files, and link it to tasks. A project's **Library** tab shows its
knowledge and documents.

## 10. Voice & writing

**Record** (pause, resume, stop, play back, then **Transcribe**) or **type or paste** text. On the
note, edit the transcript, then use **Writing tools**: clean transcript, bullet points, structured
notes, meeting or research notes, a daily update or a task breakdown — **Save as update** to record
it. **Find suggestions** proposes tasks, blockers and decisions; edit, then **Create task** /
**Record update**, **Reject** or decide **Later**. Possible duplicates of existing tasks are flagged.
Outputs marked “needs AI” are not available until an AI provider is added — they are never faked.

Press **⌘K / Ctrl+K** anywhere to search everything.

## 11. Administration

**Administration** shows health, database version and size, record counts and backup commands.

## Coming later

AI-assisted writing and planning (Phase 8) and Claude Code activity capture (Phase 9). See the roadmap.
