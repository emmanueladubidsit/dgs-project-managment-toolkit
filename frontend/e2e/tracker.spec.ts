import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

// Read a project tracker, edit one proposal, approve everything, and see the result on the board.
const RUN = `E2E-tracker ${Date.now()}`;
const FOLDER = path.join(__dirname, "_tmp_tracker");
const TRACKER = `# Progress report (written Wed 25 Nov 2026)

## 1. Week 1 (Mon 16 to Fri 20 Nov)

| Day | What was done | Evidence |
|---|---|---|
| Wed 18 | Architecture map drawn. DEMO-7 fixed. | worklog |
| Sat 21 | Bulk upload added. | worklog |

### Week 3 (30 Nov to 4 Dec), M3: identity and access
| Day | Task |
|---|---|
| Mon 30 | Login and session handling. |
`;
let projectId = "";
let demoId = "";

test.beforeAll(async ({ request }) => {
  rmSync(FOLDER, { recursive: true, force: true });
  mkdirSync(path.join(FOLDER, "docs", "project-management"), { recursive: true });
  writeFileSync(path.join(FOLDER, "docs", "project-management", "PROGRESS-AND-PLAN-2026-11-25.md"), TRACKER);
  projectId = (await (await request.post("/api/projects", { data: { name: `${RUN} project` } })).json()).id;
  demoId = (await (await request.post("/api/tasks", { data: { project_id: projectId, title: "DEMO-7: broken export" } })).json()).id;
  const c = await request.put(`/api/projects/${projectId}/connection`, { data: { path: FOLDER } });
  expect(c.ok()).toBeTruthy();
});

test.afterAll(async ({ request }) => {
  await request.delete(`/api/projects/${projectId}?confirm=${encodeURIComponent(`${RUN} project`)}`);
  rmSync(FOLDER, { recursive: true, force: true });
});

test("refresh the tracker, edit a proposal and approve all", async ({ page }) => {
  await page.goto(`/projects/${projectId}`);
  await page.getByRole("tab", { name: /Tracker/ }).click();
  await page.getByRole("button", { name: "Refresh tracker" }).click();
  await expect(page.getByText("PROGRESS-AND-PLAN-2026-11-25.md").first()).toBeVisible();
  // Saturday's work is counted on Monday.
  await expect(page.getByText("Includes weekend work from Sat 21 Nov, counted on Monday.")).toBeVisible();

  const plan = page.getByRole("region", { name: "M3: identity and access" });
  await plan.getByRole("button", { name: /Edit/ }).click();
  await plan.getByLabel("Title").fill("Login with single sign-on");
  await page.getByRole("button", { name: /^Approve all/ }).click();
  await expect(page.getByText("Nothing to review")).toBeVisible();

  const tasks = await (await page.request.get(`/api/tasks?project_id=${projectId}`)).json();
  const byTitle = Object.fromEntries(tasks.map((t: { title: string }) => [t.title, t]));
  expect(byTitle["DEMO-7: broken export"].id).toBe(demoId); // matched by its ID, not duplicated
  expect(byTitle["DEMO-7: broken export"].status).toBe("completed");
  expect(byTitle["Login with single sign-on"].scheduled_date).toBe("2026-11-30");
  expect(byTitle["Bulk upload added"].status).toBe("completed");

  await page.getByRole("tab", { name: "Board" }).click();
  await expect(page.getByText("Login with single sign-on")).toBeVisible();
});
