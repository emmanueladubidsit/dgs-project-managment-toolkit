# API design

REST over JSON, served by FastAPI at `http://localhost:8010/api`. Interactive OpenAPI docs:
**http://localhost:8010/docs** (always the authoritative, up-to-date reference).

## Conventions

- Resource paths, plural nouns; UUID identifiers.
- `POST` creates (201), `PATCH` partially updates (only supplied fields change; explicit `null`
  clears a field), `DELETE` returns 204.
- Actions that are not plain CRUD are sub-resources: `/projects/{id}/archive`, `/tasks/bulk`,
  `/planner/carry-forward`, `/reports/generate`.
- Dates are `YYYY-MM-DD`; timestamps are ISO 8601 with time zone.
- List filters are query parameters; repeated parameters mean "any of"
  (`/tasks?status=todo&status=blocked`).

## Errors

Every error has one shape:

```json
{ "error": { "code": "validation_error", "message": "Due date cannot be before the start date.", "details": [...] } }
```

| Status | `code` examples | When |
| --- | --- | --- |
| 400 | `invalid_request`, `confirmation_required` | Business rule broken, or a destructive action was not confirmed |
| 404 | `not_found` | Unknown record |
| 409 | `conflict`, `integrity_error` | Duplicate dependency, constraint clash |
| 422 | `validation_error` | Field validation; `details` lists `{field, message}` |
| 500 | `internal_error` | Unexpected; details are logged server-side only |

Messages are written in plain British English so the frontend can show them directly.

## Destructive operations

- `DELETE /api/tasks/{id}?confirm=true` — permanently deletes a task and its subtasks.
- `DELETE /api/projects/{id}?confirm=<exact project name>` — permanently deletes a project.
- `DELETE /api/knowledge/{id}?confirm=true`, `DELETE /api/methodologies/{id}?confirm=true` (refused while adopted), `DELETE /api/document-roots/{id}?confirm=true` (index records only — files are never touched).
- Archive endpoints are the reversible alternative.

## Endpoints

| Method | Path | Summary |
| --- | --- | --- |
| `GET` | `/api/stages` | List Stages |
| `POST` | `/api/stages` | Create Stage |
| `PATCH` | `/api/stages/{stage_id}` | Update Stage |
| `GET` | `/api/projects` | List Projects |
| `POST` | `/api/projects` | Create Project |
| `GET` | `/api/projects/{project_id}` | Get Project |
| `PATCH` | `/api/projects/{project_id}` | Update Project |
| `DELETE` | `/api/projects/{project_id}` | Delete Project |
| `POST` | `/api/projects/{project_id}/archive` | Archive Project |
| `POST` | `/api/projects/{project_id}/restore` | Restore Project |
| `GET` | `/api/projects/{project_id}/workstreams` | List Workstreams |
| `POST` | `/api/projects/{project_id}/workstreams` | Create Workstream |
| `PATCH` | `/api/workstreams/{workstream_id}` | Update Workstream |
| `DELETE` | `/api/workstreams/{workstream_id}` | Delete Workstream |
| `GET` | `/api/milestones` | List All Milestones |
| `POST` | `/api/projects/{project_id}/milestones` | Create Milestone |
| `GET` | `/api/milestones/{milestone_id}` | Get Milestone |
| `PATCH` | `/api/milestones/{milestone_id}` | Update Milestone |
| `DELETE` | `/api/milestones/{milestone_id}` | Delete Milestone |
| `GET` | `/api/tasks` | List Tasks |
| `POST` | `/api/tasks` | Create Task |
| `GET` | `/api/tasks/{task_id}` | Read Task |
| `PATCH` | `/api/tasks/{task_id}` | Patch Task |
| `DELETE` | `/api/tasks/{task_id}` | Delete Task |
| `POST` | `/api/tasks/bulk` | Bulk Update |
| `POST` | `/api/tasks/{task_id}/archive` | Archive Task |
| `POST` | `/api/tasks/{task_id}/restore` | Restore Task |
| `POST` | `/api/tasks/{task_id}/dependencies` | Create Dependency |
| `DELETE` | `/api/tasks/{task_id}/dependencies/{depends_on_id}` | Remove Dependency |
| `GET` | `/api/tasks/{task_id}/comments` | List Comments |
| `POST` | `/api/tasks/{task_id}/comments` | Add Comment |
| `GET` | `/api/tasks/{task_id}/activity` | Task Activity |
| `GET` | `/api/activity` | Recent Activity |
| `GET` | `/api/planner/day` | Day Plan |
| `GET` | `/api/planner/week` | Week Plan |
| `GET` | `/api/planner/month` | Month Plan |
| `PUT` | `/api/planner/notes` | Upsert Note |
| `POST` | `/api/planner/carry-forward` | Carry Forward |
| `GET` | `/api/projects/{project_id}/plan-check` | Plan Check |
| `GET` | `/api/work-logs` | List Work Logs |
| `POST` | `/api/work-logs` | Create Work Log |
| `PATCH` | `/api/work-logs/{log_id}` | Update Work Log |
| `DELETE` | `/api/work-logs/{log_id}` | Delete Work Log |
| `POST` | `/api/reports/generate` | Generate Report |
| `GET` | `/api/reports` | List Reports |
| `POST` | `/api/reports` | Save Report |
| `GET` | `/api/reports/{report_id}` | Get Report |
| `PATCH` | `/api/reports/{report_id}` | Update Report |
| `DELETE` | `/api/reports/{report_id}` | Delete Report |
| `GET` | `/api/dashboard` | Dashboard |
| `GET` | `/api/health` | Health |
| `GET` | `/api/admin/system` | System Info |
| `GET` | `/api/knowledge/templates` | Templates |
| `GET` | `/api/knowledge` | List Knowledge |
| `POST` | `/api/knowledge` | Create Knowledge |
| `GET` | `/api/knowledge/{item_id}` | Get Knowledge |
| `PATCH` | `/api/knowledge/{item_id}` | Update Knowledge |
| `DELETE` | `/api/knowledge/{item_id}` | Delete Knowledge |
| `GET` | `/api/knowledge/{item_id}/versions` | List Versions |
| `POST` | `/api/knowledge/{item_id}/restore-version/{version}` | Restore Version |
| `POST` | `/api/knowledge/{item_id}/archive` | Archive Knowledge |
| `POST` | `/api/knowledge/{item_id}/restore` | Unarchive Knowledge |
| `POST` | `/api/knowledge/{item_id}/projects` | Link Project |
| `DELETE` | `/api/knowledge/{item_id}/projects/{project_id}` | Unlink Project |
| `POST` | `/api/knowledge/{item_id}/tasks` | Link Task |
| `DELETE` | `/api/knowledge/{item_id}/tasks/{task_id}` | Unlink Task |
| `POST` | `/api/knowledge/{item_id}/relations` | Add Relation |
| `DELETE` | `/api/knowledge/relations/{relation_id}` | Delete Relation |
| `POST` | `/api/knowledge/from-work-log/{log_id}` | Promote Work Log |
| `GET` | `/api/search` | Search |
| `GET` | `/api/methodologies` | List Methodologies |
| `POST` | `/api/methodologies` | Create Methodology |
| `GET` | `/api/methodologies/{mid}` | Get Methodology |
| `PATCH` | `/api/methodologies/{mid}` | Update Methodology |
| `DELETE` | `/api/methodologies/{mid}` | Delete Methodology |
| `PUT` | `/api/methodologies/{mid}/structure` | Replace Structure |
| `POST` | `/api/methodologies/{mid}/publish` | Publish |
| `POST` | `/api/methodologies/{mid}/deprecate` | Deprecate |
| `GET` | `/api/methodologies/{mid}/versions` | Versions |
| `POST` | `/api/methodologies/{mid}/duplicate` | Duplicate |
| `POST` | `/api/methodologies/from-project/{project_id}` | From Project |
| `POST` | `/api/methodologies/{mid}/archive` | Archive |
| `POST` | `/api/methodologies/{mid}/restore` | Restore |
| `GET` | `/api/projects/{project_id}/methodologies` | List Adoptions |
| `POST` | `/api/projects/{project_id}/methodologies` | Adopt |
| `PATCH` | `/api/project-deliverables/{did}` | Update Project Deliverable |
| `DELETE` | `/api/project-methodologies/{aid}` | Remove Adoption |
| `GET` | `/api/document-roots` | List Roots |
| `POST` | `/api/document-roots` | Register Root |
| `DELETE` | `/api/document-roots/{rid}` | Unregister Root |
| `POST` | `/api/document-roots/{rid}/scan` | Scan Root |
| `POST` | `/api/document-roots/{rid}/register` | Register Files |
| `GET` | `/api/documents` | List Documents |
| `POST` | `/api/documents` | Create Document |
| `GET` | `/api/documents/{did}` | Get Document |
| `PATCH` | `/api/documents/{did}` | Update Document |
| `DELETE` | `/api/documents/{did}` | Delete Document |
| `GET` | `/api/documents/{did}/preview` | Preview |
| `POST` | `/api/documents/{did}/archive` | Archive Document |
| `POST` | `/api/documents/{did}/restore` | Restore Document |
| `POST` | `/api/documents/{did}/tasks` | Link Task |
| `DELETE` | `/api/documents/{did}/tasks/{task_id}` | Unlink Task |
| `GET` | `/api/voice/status` | Voice Status |
| `GET` | `/api/voice/notes` | List Notes |
| `POST` | `/api/voice/notes` | Upload Recording |
| `POST` | `/api/voice/notes/text` | Create Text Note |
| `GET` | `/api/voice/notes/{nid}` | Get Note |
| `PATCH` | `/api/voice/notes/{nid}` | Update Note |
| `DELETE` | `/api/voice/notes/{nid}` | Delete Note |
| `GET` | `/api/voice/notes/{nid}/audio` | Get Audio |
| `DELETE` | `/api/voice/notes/{nid}/audio` | Delete Audio |
| `POST` | `/api/voice/notes/{nid}/transform` | Transform |
| `POST` | `/api/voice/notes/{nid}/save-as-update` | Save As Update |
| `POST` | `/api/voice/notes/{nid}/suggestions` | Suggest |
| `GET` | `/api/suggestions` | List Suggestions |
| `PATCH` | `/api/suggestions/{sid}` | Edit Suggestion |
| `POST` | `/api/suggestions/{sid}/approve` | Approve, with optional edits (title, status, progress, milestone, workstream, dates) |
| `POST` | `/api/suggestions/approve-batch` | Approve several (milestones first); per-item results |
| `POST` | `/api/suggestions/{sid}/reject` | Reject |
| `POST` | `/api/suggestions/{sid}/defer` | Defer |
| `GET` | `/api/ai/status` | Status |
| `PUT` | `/api/ai/settings` | Update Settings |
| `POST` | `/api/ai/test` | Test Connection |
| `GET` | `/api/ai/models` | Models |
| `GET` | `/api/ai/usage` | Usage |
| `POST` | `/api/ai/write` | Write |
| `POST` | `/api/ai/ask` | Ask |
| `POST` | `/api/ai/suggest` | Suggest |
| `POST` | `/api/ai/breakdown/{task_id}` | Breakdown |
| `POST` | `/api/ai/structure-project` | Structure Project |
| `POST` | `/api/ai/research-draft` | Research Draft |
| `POST` | `/api/ai/report-summary` | Report Summary |
| `POST` | `/api/export` | Export Markdown |
| `GET` | `/api/export/report/{report_id}` | Export Report |
| `GET` | `/api/export/project/{project_id}/{kind}` | Export Project |
| `GET` | `/api/export/knowledge/{item_id}` | Export Knowledge |
| `GET` | `/api/connections` | List Connections |
| `GET` | `/api/projects/{project_id}/connection` | Get Connection |
| `PUT` | `/api/projects/{project_id}/connection` | Connect |
| `DELETE` | `/api/projects/{project_id}/connection` | Disconnect |
| `POST` | `/api/projects/{project_id}/sync` | Sync Now (also refreshes the tracker) |
| `POST` | `/api/projects/{project_id}/tracker/refresh` | Read the newest tracker and propose changes (ADR 0010) |
| `GET` | `/api/tracker/instructions` | CLAUDE.md text describing the tracker format |
| `GET` | `/api/settings/projects` | Projects folder (`root`, `exists`, `source`) |
| `PUT` | `/api/settings/projects` | Set the projects folder (`create: true` creates it) |
| `GET` | `/api/project-discovery` | Project folders in the projects folder that are not connected yet |
| `POST` | `/api/project-discovery/add` | Create and connect a project for a discovered folder |
| `POST` | `/api/project-discovery/start` | Create a new project folder with a tracker and CLAUDE.md, then the project |
| `GET` | `/api/projects/{project_id}/code-events` | Code Events |
| `POST` | `/api/code-events/{event_id}/save-as-update` | Save Event As Update |
| `GET` | `/api/claude/setup` | Setup |
| `POST` | `/api/claude/events` | Claude Event |
| `GET` | `/api/claude/settings` | Claude Settings (task sharing, off by default) |
| `PUT` | `/api/claude/settings` | Save Claude Settings |
| `GET` | `/api/claude/context` | Mcp Context (403 unless sharing is allowed) |
| `POST` | `/api/claude/report` | Mcp Report |
| `POST` | `/api/claude/update` | Mcp Update |
| `GET` | `/api/privacy/names` | Get Names |
| `PUT` | `/api/privacy/names` | Put Names |

## Uploads

`POST /api/voice/notes` takes `multipart/form-data` (`audio`, `title`, optional `project_id`).
Accepted types: WebM, Ogg, MP4/M4A, MP3, WAV, AIFF; maximum size `MAX_UPLOAD_MB` (default 50).
Returns 503 `transcription_unavailable` when no provider is configured — nothing is stored.

To regenerate this table: `curl -s localhost:8010/openapi.json` and list `paths`.
