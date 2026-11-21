# PROJECT: DGS PROJECT & ENGINEERING INTELLIGENCE WORKSPACE

## 1. YOUR ROLE

Act as a senior product engineer, software architect, full-stack developer, UX/UI designer, database architect and quality assurance engineer.

Your responsibility is to design and build a working MVP of a local-first, AI-assisted Personal Project & Engineering Intelligence Workspace.

You must approach this as a real software product, not a demonstration or a collection of disconnected screens.

You are responsible for:

- Understanding the product vision.
- Inspecting the existing development environment and repository before making changes.
- Defining a practical MVP architecture.
- Designing a consistent and accessible user interface.
- Implementing the frontend, backend and database.
- Building functional project and task management.
- Creating the foundations for knowledge management, reusable methodologies and AI-assisted workflows.
- Writing and maintaining technical documentation.
- Testing the application throughout development.
- Ensuring the application can be run and demonstrated locally.
- Providing clear setup, usage and troubleshooting instructions.

Do not merely generate a plan or prototype. The objective is to deliver a working application that I can use to manage real projects and track my daily work.

---

# 2. PRODUCT VISION

Build a personalized workspace that helps me manage projects from initial ideation through research, planning, design, development, testing, evaluation, deployment and maintenance.

The application should bring together project management, task planning, research, technical documentation, reusable knowledge, Claude Code activity, voice-assisted productivity and reporting.

Its central purpose is to eliminate repetitive work, improve visibility of project delivery, structure how I work and ensure that knowledge gained from one project can be reused in future projects.

The application should become more valuable as more projects are completed.

The guiding principle is:

"Every discussion should be capable of becoming knowledge. Every piece of knowledge should be capable of becoming an artefact. Every artefact should be capable of informing a task. Every task should contribute to a milestone. Every milestone should contribute to a project outcome. Every completed project should make the next project easier."

The application should be local-first, modular, maintainable and designed so it can be deployed to cloud infrastructure in the future without requiring a fundamental architectural rewrite.

Use British English throughout the application.

---

# 3. PRIMARY MVP OBJECTIVE

Prioritise a working MVP that allows me to:

1. Create and manage projects.
2. Define project objectives, descriptions, scope and expected outcomes.
3. Break projects into workstreams, milestones, epics, tasks and subtasks.
4. Plan work over monthly, weekly and daily periods.
5. Track task status, priority, estimated effort, deadlines and progress.
6. View tasks using a Kanban board, list and calendar/planner interface.
7. Record daily progress and work updates.
8. Generate daily and weekly progress reports.
9. Capture project decisions, research, issues and documentation.
10. Store reusable knowledge, templates and methodologies.
11. Review project progress and understand what remains to be completed.
12. Preserve project history so completed work can inform future projects.

The MVP must be usable without requiring a paid AI API.

Core project management, task management, planning, knowledge storage and reporting must work deterministically.

AI-assisted features should be optional and introduced through a provider-independent architecture.

Do not sacrifice working task management to build advanced AI functionality.

---

# 4. PRODUCT MODULES

Design the application around the following modules. Distinguish between features required for the initial MVP and capabilities that should be introduced in later phases.

## MODULE A: PROJECT MANAGEMENT

This is the foundation of the application.

Users must be able to create, edit, archive and manage projects.

Each project should support:

- Project name.
- Project description.
- Problem statement.
- Project objectives.
- Target users.
- Business context.
- Scope and out-of-scope areas.
- Expected outcomes.
- Start date.
- Target completion date.
- Project status.
- Priority.
- Progress.
- Stakeholders or contacts, where applicable.
- Dependencies.
- Risks and assumptions.
- Technology stack.
- Repository location or URL.
- Project documentation location.
- Project notes.
- Associated knowledge and artefacts.

Support project lifecycle stages such as:

- Discovery.
- Research.
- Requirements.
- Design.
- Prototype.
- Approval.
- Development.
- Testing.
- Staging.
- Production.
- Maintenance.
- Archived.

These stages must be configurable and must not impose an unnecessarily rigid workflow.

A project overview should provide a useful summary of its status, milestones, tasks, upcoming deadlines, blockers, risks and recent activity.

## MODULE B: WORKSTREAMS, MILESTONES AND TASK MANAGEMENT

This is the highest-priority module.

Implement a proper hierarchical planning system:

Project → Workstream/Epic → Milestone → Task → Subtask.

Allow tasks to be associated with one or more relevant project entities without creating unnecessary duplication.

Typical workstreams include:

- Product and requirements.
- Research and discovery.
- UX/UI and design system.
- Frontend development.
- Backend/API development.
- Database and data architecture.
- AI and agent implementation.
- AI evaluation.
- Software testing and quality assurance.
- Security, privacy and governance.
- Integrations.
- Infrastructure and deployment.
- Documentation.
- Stakeholder engagement.
- Maintenance and operations.

Workstreams must be configurable because not every project needs every category.

### Task fields

Each task should support:

- Title.
- Detailed description.
- Project.
- Workstream or epic.
- Milestone.
- Parent task, where applicable.
- Status.
- Priority.
- Start date.
- Due date.
- Estimated effort.
- Actual effort, where available.
- Progress percentage.
- Dependencies.
- Acceptance criteria.
- Expected deliverables.
- Assignee (single-user initially, with future multi-user support considered).
- Labels and categories.
- Notes.
- Linked documents and knowledge.
- Creation date.
- Last updated date.
- Completion date.
- Activity history.

### Task statuses

Support:

- To Do.
- In Progress.
- Blocked.
- In Review.
- Completed.
- Cancelled.

Allow configuration of statuses in future.

Task status and percentage progress must be separate concepts.

A task can be In Progress at 40%, for example.

Support priority levels:

- Critical.
- High.
- Medium.
- Low.

### Task management functionality

Implement:

- Create, edit, delete and archive tasks.
- Create subtasks.
- Reorder tasks.
- Move tasks between statuses.
- Add dependencies.
- Identify blocked tasks.
- Add comments and updates.
- Link tasks to milestones and deliverables.
- Filter and search tasks.
- Sort by priority, deadline, status and project.
- Bulk update where appropriate.
- Track changes in task history.
- View overdue and upcoming tasks.
- View completed work.

Deleting important records should use confirmation and appropriate safeguards.

### Progress calculations

Project and milestone progress should be calculated transparently.

Do not calculate progress solely from the number of completed tasks if the tasks have significantly different importance.

Support weighted progress where appropriate, while clearly showing how it is calculated.

Do not automatically mark parent tasks, milestones or projects as complete simply because some child tasks have been updated.

Provide clear progress indicators and explanations.

## MODULE C: PROJECT PLANNING AND DAILY EXECUTION

The application must translate project goals into an actionable delivery plan.

Support three planning levels:

### Monthly planning

Show:

- Monthly objectives.
- Target milestones.
- Expected deliverables.
- Major dependencies.
- Risks.
- Planned versus actual progress.

### Weekly planning

Show:

- Weekly objectives.
- Tasks planned.
- Priority order.
- Expected outputs.
- Upcoming milestones.
- Dependencies.
- Carry-over tasks.
- Weekly progress.

### Daily planning

Provide a dedicated daily planner.

Show:

- Today's objectives.
- Tasks scheduled for today.
- Priorities.
- Estimated effort.
- Task deadlines.
- Time allocation, if available.
- Blockers.
- Tasks carried forward.
- Completed tasks.
- Unplanned work.

Allow tasks to be scheduled, rescheduled and moved between days.

The planner should respect available working hours and task estimates where those details have been supplied.

Do not invent working hours or assume every day is available for project work.

### Delivery planning

Allow a project target duration, for example two or three months.

Provide a planning workflow that can distribute tasks and milestones across the target period.

The application should identify:

- Dependencies.
- Potential bottlenecks.
- Unrealistic deadlines.
- Excessive workloads.
- Missing tasks.
- Milestones with no associated deliverables.
- Tasks without acceptance criteria.

AI-assisted planning may be introduced later, but deterministic scheduling and manual editing must work in the MVP.

## MODULE D: PROJECT DISCOVERY AND CONTEXT BUILDER

Create a guided project initiation workflow.

When starting a project, I should be able to provide an initial idea in natural language.

The application should help organise it into:

- Project overview.
- Problem statement.
- Business context.
- Target users.
- Objectives.
- User needs.
- Scope.
- Features.
- Functional requirements.
- Non-functional requirements.
- Technical constraints.
- Assumptions.
- Risks.
- Dependencies.
- Unknowns.
- Expected deliverables.

The workflow should help identify missing information and distinguish confirmed requirements from assumptions.

Allow the resulting project context to be edited and expanded.

Do not require every field to be completed before creating a project.

## MODULE E: IDEATION TO TASK GENERATION

Brainstorming and planning should be connected to actual project execution.

Allow me to capture ideas, discussions, research findings, meeting notes and decisions.

A future AI-assisted workflow should be able to:

1. Analyse the captured information.
2. Identify proposed actions.
3. Identify new requirements.
4. Identify potential deliverables.
5. Identify dependencies.
6. Suggest tasks and subtasks.
7. Recommend workstreams.
8. Associate tasks with milestones.
9. Suggest priority and effort estimates.
10. Identify missing acceptance criteria.

All AI-generated tasks must initially be suggestions or drafts.

I must be able to review, edit, approve, reject or defer them before they enter the official project backlog.

Never create duplicate tasks simply because the same subject appears in multiple conversations.

## MODULE F: KNOWLEDGE, RESEARCH AND DOCUMENTATION

Create a dedicated knowledge and research area.

The purpose is to preserve useful knowledge gained during project work so it can be reused in other projects.

Support these knowledge categories:

- Research.
- Troubleshooting guides.
- Technical runbooks.
- Methodologies.
- Playbooks.
- Technical standards.
- Design standards.
- Architecture patterns.
- Decisions.
- Lessons learned.
- Templates.
- Reusable components.
- Setup guides.
- Checklists.
- Project documentation.

### Research records

Each research record should support:

- Research title.
- Research question.
- Objective.
- Project association.
- Date.
- Researcher/source.
- Sources and references.
- Findings.
- Options investigated.
- Comparisons.
- Conclusions.
- Recommendations.
- Limitations.
- Outstanding questions.
- Related decisions.
- Related artefacts.
- Reuse suitability.
- Verification status.

For example, preserve research into combining different design systems, including how colours, typography, spacing, buttons, forms and other components were standardised.

### Troubleshooting and technical guides

Capture problems and their solutions in a repeatable format:

- Problem.
- Symptoms.
- Environment.
- Root cause.
- Investigation steps.
- Commands and tools used.
- Resolution steps.
- Verification.
- Prevention.
- Limitations.
- Related code changes.
- Related project.
- Related Claude session.
- Sources and references.

The goal is to allow me to follow a guide later without needing Claude.

### Knowledge verification

Distinguish clearly between:

- Verified and tested.
- Verified against official documentation.
- Successfully applied in a project.
- Research findings not yet implemented.
- AI-generated suggestions awaiting review.
- Outdated or superseded information.

Never present an unverified AI-generated answer as established fact.

## MODULE G: REUSABLE METHODOLOGIES, PLAYBOOKS AND STARTER KITS

This is a core product capability.

Create a global library of reusable methodologies and artefacts, separate from individual project records.

A methodology should define:

- Purpose.
- When to use it.
- Prerequisites.
- Stages.
- Activities.
- Instructions.
- Expected outputs.
- Required artefacts.
- Validation criteria.
- Tools.
- Relevant templates.
- Dependencies.
- Common risks.
- Completion criteria.

Initial methodology examples:

1. Starting a new software project.
2. Assessing an existing codebase.
3. Conducting domain and technical research.
4. Performing an architecture assessment.
5. Designing a future-state architecture.
6. Creating a design system.
7. Building a clickable prototype.
8. Developing an AI application.
9. Developing an agentic AI system.
10. Conducting AI evaluation.
11. Conducting software testing.
12. Preparing a deployment.
13. Troubleshooting production issues.

### Existing-codebase assessment methodology

Include a reusable workflow covering:

- Project discovery.
- Domain research.
- Repository inspection.
- Existing documentation review.
- Dependency analysis.
- Current-state architecture.
- Backend review.
- Frontend review.
- Database review.
- API review.
- Code quality.
- Security and privacy.
- Testing.
- Performance and reliability.
- Technical debt.
- Gap analysis.
- Risk assessment.
- Options analysis.
- Proposed architecture.
- Implementation roadmap.

### Artefact plans

Methodologies should define their expected deliverables.

Examples:

- Project brief.
- Research report.
- Codebase assessment.
- Current-state architecture.
- Proposed architecture.
- High-level architecture diagram.
- Detailed architecture diagram.
- Deployment architecture.
- Data architecture.
- Security architecture.
- Architecture decision records.
- Technical requirements.
- Technology stack assessment.
- Design system specification.
- Prototype.
- Testing strategy.
- AI evaluation strategy.
- Risk register.
- Delivery roadmap.
- Stakeholder presentation.

Classify deliverables as mandatory, recommended, optional or not applicable.

### Reuse across projects

Allow a user to:

- Browse global methodologies.
- Search existing knowledge.
- Reuse a complete methodology.
- Reuse individual steps.
- Reuse templates.
- Reuse technical artefacts.
- Create a starter kit.
- Adapt a methodology for a particular project.
- Record which previous project an artefact originated from.
- Track where it has subsequently been reused.

Do not blindly copy project-specific assumptions or confidential information into another project.

Preserve provenance, version history, limitations and verification status.

## MODULE H: PROJECT DOCUMENTS AND ARTEFACT LIBRARY

Provide a project document area.

Support:

- Project briefs.
- Requirements.
- Architecture documents.
- Architecture decision records.
- Design documents.
- Diagrams.
- Research.
- Reports.
- Prototypes.
- Technical specifications.
- Testing documentation.
- Release notes.
- Meeting notes.
- Presentations.

Support references to files stored in existing project directories.

Prefer indexing or linking to original files instead of duplicating them unnecessarily.

Allow users to register multiple project directories.

Do not move, delete, overwrite or modify existing project files without explicit approval.

Provide appropriate path validation and access safeguards.

For the MVP, prioritise document metadata, categorisation, linking and basic text content.

Advanced document preview and editing can be added later.

## MODULE I: CLAUDE CODE ACTIVITY CAPTURE

Design an optional integration with Claude Code.

Investigate the actual supported Claude Code session, hook and local data mechanisms before implementing this integration.

Do not invent unsupported APIs or assume access to information that is not available.

The intended functionality is to capture relevant development activity, including where supported:

- Project association.
- Session identifier.
- Start and end times.
- Session summaries.
- Files changed.
- Commands or tools used.
- Issues investigated.
- Decisions made.
- Tasks worked on.
- Errors and resolutions.
- Relevant outputs.

The application should be able to identify potential task updates and knowledge worth preserving.

For example, when Claude resolves a technical problem, the application may suggest creating a troubleshooting guide.

When Claude completes work related to an existing task, it may suggest updating the task.

All important task status changes and knowledge publication must require review and approval.

Privacy requirements:

- Do not capture full raw transcripts by default.
- Allow configuration of capture behaviour.
- Avoid collecting secrets, tokens and credentials.
- Do not expose sensitive source code or environment variables unnecessarily.
- Make the integration optional.
- The application must remain functional when Claude Code is unavailable.

Do not make this integration a blocker for the first working MVP.

## MODULE J: VOICE AND WRITING WORKSPACE

Create an architecture for voice-assisted productivity.

Planned capabilities include:

- Record.
- Pause.
- Resume.
- Stop.
- Playback.
- Transcribe.
- Edit transcript.
- Clean grammar.
- Remove unnecessary filler words.
- Improve structure.
- Preserve original meaning.

Support output types:

- Clean transcript.
- Professional rewrite.
- Concise summary.
- Bullet summary.
- Structured notes.
- Daily update.
- Weekly update.
- Requirements.
- Task breakdown.
- Meeting notes.
- Research notes.
- Email draft.
- Brainstorming record.

Use British English by default.

### Context-aware writing

Allow me to paste an email and select the relevant project.

I should be able to provide instructions by typing or speaking.

The application may use relevant project context to draft an appropriate response.

Show the context and sources used where possible.

Never invent commitments, project status, decisions or factual claims.

Never automatically send emails.

### Voice-to-task functionality

Allow spoken updates to be converted into suggested tasks, task updates, blockers and decisions.

All changes must be reviewed before being committed.

### Speech recognition architecture

Use a provider abstraction.

Investigate local speech-to-text options, such as Whisper-based solutions, and optional cloud providers.

Core application functionality must not depend on a paid transcription service.

Recording retention must be configurable, with deletion controls.

Do not store recordings unnecessarily.

Voice functionality may be phased into the MVP after core project and task management is working.

## MODULE K: REPORTING AND INSIGHTS

Provide reporting at daily, weekly, monthly and project levels.

### Daily report

Include:

- Work completed.
- Tasks updated.
- Progress.
- Decisions.
- Blockers.
- Research conducted.
- Artefacts produced.
- Next steps.

### Weekly report

Include:

- Achievements.
- Milestones progressed.
- Tasks completed.
- Tasks outstanding.
- Blockers.
- Risks.
- Decisions.
- Upcoming priorities.
- Planned versus actual progress.

### Monthly and project reporting

Include:

- Overall progress.
- Milestones.
- Deliverables.
- Schedule changes.
- Risks.
- Scope changes.
- Outstanding work.
- Lessons learned.

Support both stakeholder-friendly and technical reporting formats.

Reports should be generated from stored application data and remain editable.

Allow copying and exporting reports.

Do not invent progress or achievements.

Clearly distinguish planned work from completed work.

## MODULE L: ADMINISTRATION AND SYSTEM HEALTH

Provide a separate administration area.

Ordinary project users should not be exposed to technical administration functionality.

The admin area should eventually include:

- System health.
- Application version.
- Database status.
- Storage status.
- Integration status.
- Error logs.
- Diagnostic information.
- Activity and system observability.
- Backup and restore controls.
- Configuration.
- System settings.
- Troubleshooting.

For a single-user MVP, keep the administration experience simple.

Design role and permission boundaries so a future multi-user version can separate system administrators from ordinary project users.

Do not build a complex enterprise identity and access management system now.

---

# 5. USER EXPERIENCE AND INTERFACE DESIGN

The application should feel like a professional productivity and engineering workspace.

Use a clear, modern, consistent interface.

Take inspiration from the usability of Jira, Linear and Notion, but do not copy their interfaces.

Apply GOV.UK-style design principles where useful:

- Clarity.
- Accessibility.
- Consistency.
- Readability.
- Strong information hierarchy.
- Predictable navigation.
- Clear error messages.
- Visible system status.

Do not make the application look like a government website.

### Main navigation

Use a persistent sidebar with the following sections:

1. Dashboard.
2. Projects.
3. My Tasks.
4. Planner.
5. Milestones.
6. Knowledge & Research.
7. Methodologies & Playbooks.
8. Documents & Artefacts.
9. Voice & Writing.
10. Reports.
11. Administration.

The navigation should be organised so the main project delivery workflow is immediately accessible.

Some modules may be introduced progressively, but their placement and relationship should be considered in the design.

### Dashboard

The dashboard should show:

- Welcome and date.
- Overall project overview.
- Active projects.
- Tasks due today.
- Overdue tasks.
- Upcoming deadlines.
- Current milestones.
- Blocked tasks.
- Recent activity.
- Weekly progress.
- Quick actions.

Quick actions should include:

- New project.
- New task.
- Add daily update.
- Capture research.
- Create knowledge item.
- Start a planning session.

### Project workspace

Each project should have a dedicated workspace with sections such as:

- Overview.
- Backlog.
- Milestones.
- Planner.
- Research.
- Documents.
- Architecture.
- Decisions.
- Activity.
- Reports.

Use contextual navigation where appropriate.

### Task views

Provide:

- Kanban board.
- Task list.
- Daily planner.
- Weekly planner.
- Calendar or timeline view.

All views must be connected to the same underlying task records.

Do not build decorative or disconnected mock interfaces.

### Design system

Establish reusable design tokens and components.

Define:

- Colour palette.
- Typography.
- Spacing.
- Layout.
- Buttons.
- Inputs.
- Selectors.
- Cards.
- Tables.
- Badges.
- Dialogues.
- Navigation.
- Empty states.
- Loading states.
- Error states.

Use consistent button variants, interaction states, contrast and accessibility.

The design system should be documented so it can be reused in future projects.

---

# 6. RECOMMENDED TECHNICAL ARCHITECTURE

Use a modular monolith for the MVP.

Do not introduce microservices unless there is a clear and justified requirement.

Recommended stack:

### Frontend
- Next.js.
- TypeScript.
- Tailwind CSS.
- shadcn/ui.
- Reusable React components.

### Backend
- Python.
- FastAPI.
- Pydantic.
- REST API.
- OpenAPI documentation.

### Database
- PostgreSQL.
- SQLAlchemy.
- Alembic migrations.

### Testing
- Pytest.
- Frontend component tests.
- Playwright for end-to-end testing.

### Local infrastructure
- Docker Compose where available.
- Persistent database volumes.
- Environment-based configuration.

If Docker Desktop is unavailable, document a practical alternative for running the application and its dependencies locally.

Do not make the ability to install Docker Desktop a prerequisite for understanding or developing the application.

### Architecture principles

- Clear separation of frontend and backend.
- Modular backend services.
- Clear API contracts.
- Database migrations.
- Structured logging.
- Consistent error handling.
- Input validation.
- Environment-based configuration.
- Reusable UI components.
- Dependency management.
- Automated tests.
- Clear documentation.

Keep AI provider integrations behind interfaces so that different models or local AI services can be introduced later.

The core application must continue to work without AI services.

---

# 7. CORE DATA MODEL

Design a sensible relational data model.

At minimum, consider these entities:

- Project.
- ProjectStage.
- Workstream.
- Milestone.
- Task.
- Subtask relationship.
- TaskDependency.
- TaskComment.
- TaskActivity.
- DailyPlan.
- WeeklyPlan.
- WorkLog.
- ProjectUpdate.
- ResearchRecord.
- KnowledgeItem.
- Methodology.
- MethodologyVersion.
- MethodologyStage.
- MethodologyActivity.
- DeliverableDefinition.
- Artefact.
- Template.
- Playbook.
- StarterKit.
- DecisionRecord.
- EvidenceReference.
- ProjectDocument.
- ClaudeSession.
- VoiceNote.
- Transcript.
- Report.
- SystemSetting.
- AuditEvent.

Do not implement every advanced entity immediately.

Create the initial schema around the MVP workflows and extend it as the relevant modules are implemented.

Important relationships must be designed carefully.

For example:

- A project contains workstreams, milestones and tasks.
- Tasks may depend on other tasks.
- Tasks can be linked to research, knowledge and documents.
- A methodology contains stages and activities.
- A methodology can define expected deliverables.
- A project can adopt a methodology.
- An artefact can originate from one project and be reused by others.
- A knowledge item can be associated with multiple projects.
- Decisions should link to their supporting evidence and relevant artefacts.

Include appropriate identifiers, timestamps, validation, constraints and indexes.

Support versioning for reusable knowledge and methodologies.

Avoid unnecessary database complexity.

---

# 8. SECURITY, PRIVACY AND GOVERNANCE

Apply security and privacy principles from the beginning.

Consider:

- Input validation.
- Secure configuration.
- Secrets management.
- SQL injection prevention.
- Cross-site scripting protection.
- Appropriate access controls.
- File path validation.
- Safe file handling.
- Dependency vulnerability checks.
- Error handling that does not expose secrets.
- Safe logging.
- Backup and recovery.
- Data retention.
- Local data privacy.

Do not store API keys or passwords in source code.

Use environment variables and provide an example environment file without real credentials.

Do not commit .env files, database dumps, recordings or confidential project documents to GitHub.

Treat research and AI-generated content as untrusted until reviewed.

Provide explicit confirmation before destructive operations.

The application is initially single-user and local-first. Do not implement unnecessary enterprise infrastructure.

---

# 9. MVP IMPLEMENTATION ROADMAP

Implement incrementally in the following order.

The first objective is to produce a genuinely usable project and task management application.

## PHASE 0 — INSPECTION AND TECHNICAL FOUNDATION

Before implementation:

1. Inspect the current repository.
2. Understand the existing files and architecture.
3. Identify existing code that can be reused.
4. Identify the current development environment and constraints.
5. Check available runtimes and dependencies.
6. Determine whether the repository already contains a working application.
7. Identify risks and missing prerequisites.

Do not overwrite existing work.

Create or update:

- Product requirements document.
- Technical architecture document.
- Database design.
- API design.
- Project structure.
- Implementation roadmap.
- Development setup guide.

Explain significant architecture decisions and their trade-offs.

## PHASE 1 — DESIGN SYSTEM AND APPLICATION SHELL

Implement:

- Application layout.
- Sidebar navigation.
- Header.
- Dashboard shell.
- Design tokens.
- Reusable components.
- Responsive layout.
- Empty states.
- Error and loading states.

The application must have a consistent design system from the beginning.

## PHASE 2 — PROJECT MANAGEMENT

Implement:

- Project creation.
- Project editing.
- Project details.
- Project lifecycle status.
- Project overview.
- Project search and filtering.
- Project archive.
- Project-specific workspace.

Verify that projects persist in PostgreSQL.

## PHASE 3 — TASKS, MILESTONES AND WORKSTREAMS

This is the most important delivery phase.

Implement:

- Workstreams.
- Milestones.
- Tasks.
- Subtasks.
- Dependencies.
- Priorities.
- Statuses.
- Progress.
- Estimates.
- Due dates.
- Acceptance criteria.
- Task comments.
- Task activity history.
- Kanban board.
- Task list.
- Search and filters.

Ensure that all views use the same persistent task data.

Test all create, read, update and delete workflows.

## PHASE 4 — DAILY AND WEEKLY PLANNING

Implement:

- Daily planner.
- Weekly planner.
- Monthly overview.
- Task scheduling.
- Rescheduling.
- Carry-over tasks.
- Workload visibility.
- Upcoming deadlines.

Ensure that task updates are reflected in planning views.

## PHASE 5 — PROJECT ACTIVITY AND REPORTING

Implement:

- Daily work logs.
- Project updates.
- Daily reports.
- Weekly reports.
- Project progress summaries.
- Planned versus actual tracking.
- Editable report outputs.

Reports must be based on real application data.

## PHASE 6 — KNOWLEDGE AND RESEARCH

Implement:

- Research records.
- Knowledge items.
- Troubleshooting guides.
- Technical documentation.
- Decisions.
- Lessons learned.
- Source references.
- Project associations.
- Global search.
- Knowledge categorisation.

Ensure knowledge can be associated with multiple projects where appropriate.

## PHASE 7 — METHODOLOGIES AND REUSABLE ARTEFACTS

Implement the foundations for:

- Methodology library.
- Methodology stages.
- Activity instructions.
- Deliverable definitions.
- Reusable templates.
- Playbooks.
- Starter kits.
- Knowledge promotion.
- Reuse across projects.
- Version history.

Prioritise a functional methodology workflow over an elaborate AI-generated workflow.

## PHASE 8 — AI-ASSISTED PRODUCTIVITY

Introduce provider-independent AI capabilities:

- Brainstorming to task suggestions.
- Requirements structuring.
- Research summarisation.
- Task breakdown.
- Planning assistance.
- Knowledge extraction.
- Daily update summarisation.
- Context-aware writing.

All AI-generated changes must be reviewable.

The application must remain usable if AI is disabled.

## PHASE 9 — VOICE AND CLAUDE CODE INTEGRATION

Implement the voice and Claude Code capabilities after the core product is stable.

Use verified integration mechanisms.

Keep integrations optional.

## PHASE 10 — ADMINISTRATION, POLISH AND RELEASE

Implement:

- System health.
- Logs.
- Diagnostics.
- Database health.
- Configuration.
- Backup guidance.
- Error handling.
- Final usability improvements.
- End-to-end testing.
- Installation and operating documentation.

---

# 10. MVP ACCEPTANCE CRITERIA

The MVP is not complete simply because the interface looks finished.

The following must work.

### Project management
- I can create a project.
- I can edit and archive a project.
- Project data persists after restarting the application.
- I can view project status and progress.

### Task management
- I can create tasks and subtasks.
- I can associate tasks with projects, workstreams and milestones.
- I can set priority, status, dates and estimates.
- I can update progress.
- I can move tasks through the Kanban board.
- I can filter and search tasks.
- I can record task updates.
- I can identify blocked and overdue tasks.
- I can view task history.
- Changes persist in the database.

### Planning
- I can plan tasks for a day and week.
- I can view upcoming deadlines.
- I can reschedule unfinished tasks.
- I can track milestones.
- I can see progress against project objectives.

### Reporting
- I can generate a daily report.
- I can generate a weekly report.
- Reports reflect actual stored task and activity data.
- I can edit and copy reports.

### Knowledge
- I can create research and knowledge records.
- I can categorise them.
- I can associate them with projects.
- I can search for previously captured knowledge.
- I can create a reusable guide or template.

### General usability
- The application starts successfully.
- The database is persistent.
- The frontend communicates with the backend.
- Errors are handled appropriately.
- Empty states are useful.
- Navigation works.
- The application can be used without an AI API key.
- The application has been tested.

Do not claim an acceptance criterion has been met unless it has been verified.

---

# 11. TESTING AND QUALITY ASSURANCE

Testing is part of implementation, not a final activity.

Create:

### Backend tests
- API endpoint tests.
- Database tests.
- Model validation.
- Business logic.
- Task status transitions.
- Progress calculations.
- Task dependency behaviour.
- Reporting calculations.
- Error handling.

### Frontend tests
- Component behaviour.
- Forms.
- Navigation.
- Task interactions.
- Filtering.
- Status updates.
- Responsive layouts.

### End-to-end tests

Test a complete user journey:

1. Create a project.
2. Create a workstream.
3. Create a milestone.
4. Create tasks and subtasks.
5. Schedule tasks.
6. Update task status.
7. Record a daily update.
8. Generate a weekly report.
9. Create a research record.
10. Create a reusable knowledge item.
11. Restart the application.
12. Confirm that the records remain available.

Test important failure scenarios, not just successful workflows.

Document known defects and limitations.

---

# 12. DOCUMENTATION REQUIREMENTS

Maintain documentation throughout implementation.

At minimum:

- README.md
- docs/PRODUCT_REQUIREMENTS.md
- docs/ARCHITECTURE.md
- docs/DATABASE_DESIGN.md
- docs/API_DESIGN.md
- docs/DESIGN_SYSTEM.md
- docs/IMPLEMENTATION_ROADMAP.md
- docs/DEVELOPMENT_SETUP.md
- docs/USER_GUIDE.md
- docs/TESTING_STRATEGY.md
- docs/SECURITY_AND_PRIVACY.md
- docs/DECISIONS/

Keep documentation aligned with the actual implementation.

When architectural decisions change, update the relevant documentation.

Document setup instructions clearly enough that I can run the application without needing Claude to explain every step.

---

# 13. DEVELOPMENT WORKING RULES

These instructions are important.

### Work incrementally

Do not attempt to implement the entire application in one enormous operation.

Work in small, logically complete increments.

For each increment:

1. Explain what you intend to implement.
2. Identify the files and modules affected.
3. Implement the change.
4. Run relevant tests.
5. Check for regressions.
6. Update documentation.
7. Summarise what was completed.
8. Identify remaining work.

### Preserve user control

- Do not overwrite existing project files without understanding their purpose.
- Do not remove existing functionality without justification and approval.
- Do not make destructive database changes without appropriate safeguards.
- Do not commit secrets.
- Do not introduce unnecessary dependencies.
- Explain significant changes.
- Keep the codebase maintainable and understandable.

### Avoid overengineering

- Use a modular monolith.
- Avoid microservices.
- Avoid unnecessary abstractions.
- Avoid speculative features.
- Avoid building advanced AI agents before core workflows work.
- Do not create decorative features that do not perform real actions.
- Prefer simple, testable solutions.

### Efficient use of context and tokens

Use the existing documentation as the persistent project source of truth.

Do not repeatedly reread the entire repository when only a particular module is relevant.

Before starting a new implementation session:

1. Read the README.
2. Read the current implementation roadmap.
3. Review the relevant architecture and module documentation.
4. Inspect the files relevant to the task.
5. Identify the current implementation state.

After completing work, update the roadmap and record what has changed.

Do not spend unnecessary tokens repeating previous analysis.

If a requirement is unclear, identify it and ask a focused question where the answer materially affects the implementation.

Otherwise, make a sensible, documented assumption and continue.

---

# 14. EXPECTED FIRST ACTION

Do not start by coding random screens.

Begin by inspecting the current repository and environment.

Then:

1. Summarise what already exists.
2. Identify any existing implementation worth retaining.
3. Identify missing components.
4. Propose the MVP architecture.
5. Define the initial database schema.
6. Create the implementation roadmap.
7. Identify any major technical risks.
8. Confirm the development and execution approach.
9. Begin Phase 0 and Phase 1.

Do not spend excessive time producing documentation without delivering working software.

Once the architecture and initial design decisions are sufficiently clear, start implementing the application.

If the repository is empty, establish the project structure.

If a partially implemented application exists, build on it rather than replacing it.

---

# 15. FINAL PRODUCT EXPECTATION

The final MVP should allow me to open the application, create a real project, organise its work, create milestones, break down tasks, plan my week, track daily progress, record decisions, preserve knowledge and generate meaningful progress reports.

It should provide a solid foundation for the more advanced capabilities discussed in the product vision:

- Research intelligence.
- Reusable project methodologies.
- Technical playbooks.
- Starter kits.
- Claude Code activity capture.
- Voice transcription and writing.
- Context-aware AI assistance.
- Automated task suggestions.
- Advanced reporting.
- System administration.

These advanced capabilities must be introduced progressively without compromising the reliability of the core product.

**The immediate success measure is simple: I should be able to use this application every working day to manage my projects, know exactly what I need to do, understand what I have completed, track progress against milestones and see what remains before a project can be delivered.**

Build a real product, not just a visual prototype.