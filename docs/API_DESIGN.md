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

To regenerate this table: `curl -s localhost:8010/openapi.json` and list `paths`.
