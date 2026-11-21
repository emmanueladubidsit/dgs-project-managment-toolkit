import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { makeTask, renderWithProviders } from "@/test/utils";
import { describeActivity } from "./task-sheet";
import { KanbanBoard, TaskFilterBar, TaskTable } from "./task-views";

afterEach(() => vi.restoreAllMocks());

describe("TaskTable", () => {
  it("shows an empty state when nothing matches", () => {
    renderWithProviders(<TaskTable tasks={[]} />);
    expect(screen.getByText("No tasks match these filters.")).toBeInTheDocument();
  });

  it("flags overdue and blocked-by-dependency tasks", () => {
    renderWithProviders(<TaskTable tasks={[
      makeTask({ title: "Late", is_overdue: true, due_date: "2026-01-01" }),
      makeTask({ title: "Waiting", open_dependencies: [{ id: "x", title: "Design", status: "todo" }] }),
    ]} />);
    expect(screen.getByLabelText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("waiting on 1")).toBeInTheDocument();
  });

  it("bulk-updates the selected tasks through the API", async () => {
    const a = makeTask({ title: "Alpha" }), b = makeTask({ title: "Beta" });
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([a, b]), { status: 200, headers: { "Content-Type": "application/json" } }));
    renderWithProviders(<TaskTable tasks={[a, b]} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Select all tasks" }));
    const bar = screen.getByRole("region", { name: "Bulk actions" });
    expect(bar).toHaveTextContent("2 selected");
    await userEvent.click(within(bar).getByRole("button", { name: "Plan for today" }));
    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/tasks/bulk");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.task_ids).toEqual([a.id, b.id]);
    expect(body.changes.scheduled_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe("KanbanBoard", () => {
  it("places tasks in their status columns in position order and hides Cancelled", () => {
    renderWithProviders(<KanbanBoard tasks={[
      makeTask({ title: "Second", status: "in_progress", position: 2000 }),
      makeTask({ title: "First", status: "in_progress", position: 1000 }),
      makeTask({ title: "Done", status: "completed" }),
      makeTask({ title: "Dropped", status: "cancelled" }),
    ]} />);
    const col = screen.getByRole("listitem", { name: "In Progress column, 2 task(s)" });
    const titles = within(col).getAllByRole("button").filter((b) => !b.getAttribute("aria-label")).map((b) => b.textContent);
    expect(titles).toEqual(["First", "Second"]);
    expect(screen.getByRole("listitem", { name: "Completed column, 1 task(s)" })).toBeInTheDocument();
    expect(screen.queryByText("Dropped")).not.toBeInTheDocument();
  });
});

describe("TaskFilterBar", () => {
  it("toggles overdue and keeps the project when clearing", async () => {
    const onChange = vi.fn();
    const { rerender } = renderWithProviders(<TaskFilterBar filters={{ project_id: "p1" }} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Overdue" }));
    expect(onChange).toHaveBeenLastCalledWith({ project_id: "p1", overdue: true });
    rerender(<TaskFilterBar filters={{ project_id: "p1", overdue: true, q: "x" }} onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onChange).toHaveBeenLastCalledWith({ project_id: "p1", sort: undefined });
  });
});

describe("activity history wording", () => {
  const base = { id: "1", task_id: "t", project_id: "p", created_at: "", task_title: null };
  it("describes status and progress changes in plain English", () => {
    expect(describeActivity({ ...base, action: "updated", changes: { status: ["todo", "in_progress"], progress: [0, 40] } }))
      .toBe("Status To Do → In Progress; progress 0% → 40%");
    expect(describeActivity({ ...base, action: "created", changes: {} })).toBe("Created the task");
    expect(describeActivity({ ...base, action: "updated", changes: { acceptance_criteria: ["", "x"] } })).toBe("Edited acceptance criteria");
  });
});
