import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Suggestion } from "@/lib/types";
import { renderWithProviders } from "@/test/utils";
import { groupTracker, TrackerPanel } from "./tracker";

function sugg(id: string, kind: Suggestion["kind"], payload: Suggestion["payload"], evidence = ""): Suggestion {
  return {
    id, kind, status: "pending", source_type: "tracker", source_id: null, project_id: "p1", project_name: "P",
    generator: "tracker", payload: { tracker_file: "docs/project-management/PROGRESS-AND-PLAN-2026-11-25.md", ...payload },
    evidence, duplicate_of_task_id: null, duplicate_of_title: null, created_task_id: null, created_work_log_id: null,
  };
}

const ITEMS = [
  sugg("m3", "milestone", { title: "M3: identity", status: "planned", due_date: "2026-12-04", milestone_id: null }),
  sugg("d1", "progress", { tracker_kind: "day", title: "Work done on Mon 23 Nov 2026", item_date: "2026-11-23", entry_date: "2026-11-23", carried_from: "Sat 21 Nov" }, "Bulk upload."),
  sugg("t1", "task", { tracker_kind: "done", title: "Bulk upload", status: "completed", item_date: "2026-11-23", original_date: "2026-11-21" }),
  sugg("t0", "task", { tracker_kind: "done", title: "Architecture map", status: "completed", item_date: "2026-11-18" }),
  sugg("u1", "task_update", { tracker_kind: "status", task_id: "task-9", title: "MVP scope approved", status: "in_progress", current_status: "todo", milestone_key: "w1", milestone_title: "Week 1 milestone" }),
  sugg("p1", "task", { tracker_kind: "plan", title: "Login and sessions", status: "todo", item_date: "2026-11-30", scheduled_date: "2026-11-30", milestone_key: "m3", milestone_title: "M3: identity" }),
];

describe("groupTracker", () => {
  it("groups by working day, milestone criteria and plan week", () => {
    const g = groupTracker(ITEMS);
    expect(g.milestones.map((s) => s.id)).toEqual(["m3"]);
    expect(g.days.map((d) => d.items.map((s) => s.id))).toEqual([["t0"], ["d1", "t1"]]); // oldest day first, work log on top
    expect(g.days[1].note).toMatch(/weekend work from Sat 21 Nov/);
    expect(g.status[0].title).toBe("Week 1 milestone");
    expect(g.plan[0].title).toBe("M3: identity");
  });
});

describe("TrackerPanel", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lets you edit an item, then approves everything in one batch", async () => {
    const posts: { url: string; body: unknown }[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      const json = (d: unknown) => new Response(JSON.stringify(d), { status: 200, headers: { "Content-Type": "application/json" } });
      if (init?.method === "POST") {
        posts.push({ url, body: JSON.parse(String(init.body)) });
        return json({ approved: ITEMS.length, failed: 0, results: [] });
      }
      if (url.includes("/connection")) {
        return json({ id: "c1", project_id: "p1", tracker_file: "docs/project-management/PROGRESS-AND-PLAN-2026-11-25.md", tracker_read_at: "2026-11-25T10:00:00Z", tracker_warnings: [] });
      }
      if (url.includes("/suggestions")) return json(ITEMS);
      return json([]);
    }));
    renderWithProviders(<TrackerPanel projectId="p1" />);
    expect(await screen.findByText("6", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText(/Monday to Friday/)).toBeInTheDocument();
    expect(screen.getByText(/Done Sat,? 21 Nov 2026, counted on Mon,? 23 Nov 2026/)).toBeInTheDocument();

    const plan = screen.getByRole("region", { name: "M3: identity" });
    await userEvent.click(within(plan).getByRole("button", { name: /Edit/ }));
    const title = within(plan).getByLabelText("Title");
    await userEvent.clear(title);
    await userEvent.type(title, "Login (SSO) and sessions");

    await userEvent.click(screen.getByRole("button", { name: /Approve all 6/ }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0].url).toBe("/api/suggestions/approve-batch");
    const items = (posts[0].body as { items: { id: string; title?: string; milestone_id?: string }[] }).items;
    expect(items.map((i) => i.id).sort()).toEqual(["d1", "m3", "p1", "t0", "t1", "u1"]);
    const edited = items.find((i) => i.id === "p1")!;
    expect(edited.title).toBe("Login (SSO) and sessions");
    expect(edited.milestone_id).toBeUndefined(); // the new milestone is resolved by the server
  });

  it("asks to connect a folder first", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("null", { status: 200, headers: { "Content-Type": "application/json" } })));
    renderWithProviders(<TrackerPanel projectId="p1" />);
    expect(await screen.findByText("Connect the project's folder first")).toBeInTheDocument();
  });
});
