import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Task } from "@/lib/types";

export function renderWithProviders(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TooltipProvider>{ui}</TooltipProvider>
    </QueryClientProvider>,
  );
}

export function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: crypto.randomUUID(), project_id: "p1", project_name: "Project One", workstream_id: null,
    workstream_name: null, milestone_id: null, milestone_title: null, parent_id: null, title: "A task",
    description: null, status: "todo", priority: "medium", start_date: null, due_date: null,
    scheduled_date: null, estimate_hours: null, actual_hours: null, progress: 0, weight: null,
    acceptance_criteria: null, deliverables: null, assignee: null, labels: [], notes: null, position: 1000,
    completed_at: null, archived_at: null, created_at: "2026-11-01T09:00:00Z", updated_at: "2026-11-01T09:00:00Z",
    is_overdue: false, subtask_count: 0, subtasks_completed: 0, open_dependencies: [], ...overrides,
  };
}
