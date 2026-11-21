# Design system

Built on Tailwind CSS 4 and shadcn/ui (Radix primitives, “Nova” preset). Tokens live in
`frontend/src/app/globals.css`; reusable components in `frontend/src/components/`. It is designed
to be lifted into other projects.

## Principles

Inspired by GOV.UK principles (clarity, accessibility, consistency, readable text, strong
hierarchy, predictable navigation, clear errors, visible system status) without looking like a
government site. Usability cues from tools like Linear and Notion without copying them.

## Tokens

| Group | Tokens | Notes |
| --- | --- | --- |
| Brand | `--primary` (indigo-blue `oklch(0.46 0.17 262)`), `--primary-foreground` | Used for primary actions, active navigation, progress |
| Surfaces | `--background`, `--card`, `--muted`, `--sidebar`, `--border` | Neutral with a slight blue tint |
| Feedback | `--success`, `--warning`, `--info`, `--destructive` | Never colour alone — always paired with text or an icon |
| Task status | `--status-todo`, `-in-progress`, `-blocked`, `-in-review`, `-completed`, `-cancelled` | Badges use a 12% tint, coloured text and a dot |
| Priority | `--priority-critical`, `-high`, `-medium`, `-low` | Shown as signal bars plus a label (or screen-reader text) |
| Focus | `--focus` | 3px outline, 2px offset on every `:focus-visible` element |
| Radius | `--radius` 0.625rem with sm–4xl scale | |
| Type | Geist Sans / Geist Mono | Headings use `text-balance` |

Each token has a light and a dark value (`.dark`, toggled from the header; defaults to the
system preference).

## Components

| Component | File | Use |
| --- | --- | --- |
| Button, Input, Textarea, Select, Checkbox, Dialog, AlertDialog, Sheet, Tabs, Table, Tooltip, DropdownMenu, Skeleton, Toaster | `components/ui/*` | shadcn/ui primitives |
| `PageHeader`, `Section` | `common.tsx` | Page title + description + actions; titled card |
| `StatusBadge`, `PriorityBadge` | `common.tsx` | Consistent status and priority display |
| `ProgressBar`, `ExplainedProgress` | `common.tsx` | ARIA progressbar; the explained variant shows *how* progress was calculated |
| `EmptyState`, `ErrorState`, `LoadingState`, `QueryView` | `common.tsx` | Every data view has all three states |
| `Field`, `TextField`, `TextAreaField`, `SelectField` | `form-fields.tsx` | Labelled fields; “(required)” in the label; hints below |
| `ConfirmDialog` | `confirm-dialog.tsx` | Destructive confirmation, optional type-to-confirm |
| `KanbanBoard`, `TaskTable`, `TaskFilterBar`, `TaskRow` | `task-views.tsx` | Task views |
| `PlannedModule` | `planned-module.tsx` | Honest placeholder for unbuilt modules |

## Interaction and accessibility rules

- Every control has a visible label or an `aria-label`. Radix `Select` triggers must be named
  directly — wrapping them in `<label>` does not name them (found and fixed via E2E tests).
- Drag and drop always has a keyboard alternative (card ⋯ menu, “Planned for” field).
- Skip-to-content link; `aria-current` on active navigation; landmarks (`nav`, `main`, `header`).
- Destructive buttons use the destructive variant and a confirmation dialog.
- Errors use the API's plain-English message; toasts confirm successful actions.
- Layout is responsive: sidebar collapses to a sheet below `lg`; grids collapse to one column.
- Dates are shown in en-GB format (“21 Nov 2026”).
