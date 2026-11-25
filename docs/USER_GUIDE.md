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
project and a stakeholder or technical format, then **Generate**. The draft opens as a formatted
**Preview**: an *At a glance* summary, then sections grouped under one heading per project (weekly
achievements are dated by working day; weekend work counts on Monday). Status changes show first →
last; newly added tasks are counted rather than listed (listed in the technical format). Use the
**Edit** tab to change the text, then **Copy**, **Download**, **Word**, **PDF**, **Slides** or **Save**.
Reports contain only recorded data: sections with nothing recorded are left out and named in one
closing line (e.g. “No risks, decisions or research recorded this week”).

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

## 11. Assistant (optional AI)

Turn it on in **Administration → AI assistant** (see DEVELOPMENT_SETUP). Then use **Assistant**:
**Ask** about one project or everything (quick questions included); **Write** an email reply,
weekly update, requirements, summary or rewrite using a project's context; **Notes → tasks** to
get suggested tasks with priorities, estimates and acceptance criteria to approve; **New project
from an idea** to get a draft brief that opens in the project form; **Research draft** to create a
research record saved as “AI suggestion — awaiting review”. Each answer shows the workspace
records it was given. AI also appears where you work: **Suggest with AI** for subtasks in a task,
AI outputs and **Find with AI** on voice notes, and **Add AI executive summary** in reports.
In copy-and-paste mode, each request opens a window with the prompt to copy into your chat and a
box to paste its answer.

## 12. Share with stakeholders

- **Project → Export:** status update (PowerPoint, PDF or Word), project brief (Word or PDF) or the
  full project report.
- **Reports:** export a draft or saved report as Word, PDF or slides.
- **Knowledge item → Export:** Word or PDF (unverified items carry a warning).
- **Assistant answers and drafts:** download as Word or PDF.

Exports are generated from what is recorded at that moment, and say so in their footer.

## 13. Connect codebases and Claude Code

On a project's **Codebase** tab, enter the project's folder and **Connect folder**. The workspace
shows commits (message and changed files), uncommitted changes and Claude Code session summaries,
and checks for new commits every few minutes (or **Sync now**). A commit like “Fix ISSUE-0001”
suggests marking that task done; suggestions appear under **Updates waiting for your review** on
the tab and on the dashboard — **Apply**, **Reject** or **Later** (or **Apply all**).

Claude Code progress is picked up with nothing to set up: the workspace reads the progress files
in the folder (PROGRESS.md, issue indexes, worklogs, backlogs, CHANGELOG) on this computer only.
Items marked done (“Done”, “Closed”, ✅, `- [x]`) next to a task ID or title become suggestions.
Edit the list of files under **Change settings → Progress files to read**. Optional direct Claude
tools are under **Administration → Claude Code**; they change Claude Code's settings and share
task data with Claude, so use them only if your organisation allows it (task sharing is off by
default). Add people's names under **Administration → Privacy** to have them masked.

### Project tracker (work done each day)

Each project keeps a tracker at `docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md` (Claude
Code writes it; the newest date wins). On the project's **Tracker** tab, press **Refresh tracker**
(the background sync also does this). The workspace proposes, grouped by working day:

- **Work done** each day: matching tasks marked done, new done tasks, and one work-log entry per day.
- **Milestones** (`Week 1 milestone`, `M3: …`) with their status and due date, and the
  **milestone criteria** (Verified → Completed, In progress, Not started → To do).
- **The plan**: to-do tasks on their planned day under their milestone, or a new planned day for an
  existing task.

Working days are **Monday to Friday**: anything done on a Saturday or Sunday is counted on the
following Monday. Click **Edit** on any item to change its title, status, progress, milestone,
workstream or dates, then **Approve**, **Reject** or **Later**, or approve a whole day, section or
everything at once. Nothing changes until you approve. Items flagged “possibly the same as …”
probably already exist: reject them if so. Rejected items are not proposed again.

### Projects folder and discovery

Keep technical projects in one folder (set under **Administration → Projects folder**; here
`MY RESEARCH & WORK/Projects`). On **Projects**:

- **Discover projects** lists project folders there that are not connected yet; **Add** creates the
  project and connects its folder (read only).
- **Start a new project** creates the folder with a starter tracker and a `CLAUDE.md` telling
  Claude Code how to keep it. Nothing existing is overwritten.

For an existing project, copy the tracker instructions from **Administration → Projects folder**
into its `CLAUDE.md`.

### Keep AI answers (browser extension)

Use ChatGPT, Claude, Gemini or Copilot in your browser, signed in with your own account. With the
**Keep to DGS** extension installed (**Administration → Browser extension**), tick **Keep** on the
answers you want (or select text and press **Keep selection**). In the Keep bar, choose the project,
or **New project…**, and save as a note (it appears in the project's Library with a link back to the
chat) or as a progress update. On a code block, **Add to file** lets you choose the project and the
path, **Preview** the new file or the before/after, then **Write file**. Writing must first be
allowed in Administration, and only works inside the project's connected folder. Nothing else
from the chat is stored.

## 14. Administration

**Administration** shows health, database version and size, record counts, backup commands and
the projects folder.

## Coming later

See the roadmap for what comes next.
