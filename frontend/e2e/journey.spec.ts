import { expect, test, type Page } from "@playwright/test";

// The complete MVP journey from the product brief (section 11). Data is uniquely named and
// removed afterwards so the test never pollutes real workspace data.
const RUN = `E2E ${Date.now()}`;
const PROJECT = `${RUN} project`;
const today = new Date();
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const TODAY = iso(today);
let projectId = "";
const cleanupKnowledge: string[] = [];

async function choose(page: Page, scope: ReturnType<Page["getByRole"]>, label: string, option: string) {
  await scope.getByLabel(label, { exact: true }).click();
  await page.getByRole("option", { name: option, exact: true }).click();
}

test.afterAll(async ({ request }) => {
  for (const id of cleanupKnowledge) await request.delete(`/api/knowledge/${id}?confirm=true`);
  if (!projectId) return;
  const logs = await (await request.get(`/api/work-logs?project_id=${projectId}`)).json();
  for (const l of logs) await request.delete(`/api/work-logs/${l.id}`);
  await request.delete(`/api/projects/${projectId}?confirm=${encodeURIComponent(PROJECT)}`);
});

test("project → workstream → milestone → tasks → plan → update → report → persistence", async ({ page }) => {
  // 1. Create a project
  await page.goto("/projects");
  await page.getByRole("button", { name: "New project" }).first().click();
  const projectDialog = page.getByRole("dialog");
  await projectDialog.getByLabel("Project name (required)").fill(PROJECT);
  await projectDialog.getByLabel("Objectives").fill("Prove the MVP journey works end to end");
  await projectDialog.getByRole("button", { name: "Create project" }).click();
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}$/);
  projectId = page.url().split("/").pop()!;
  await expect(page.getByRole("heading", { level: 1, name: PROJECT })).toBeVisible();

  // 2. Create a workstream
  await page.getByRole("tab", { name: "Workstreams" }).click();
  await page.getByLabel("New workstream name").fill("E2E workstream");
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("E2E workstream", { exact: true })).toBeVisible();

  // 3. Create a milestone
  await page.getByRole("tab", { name: "Milestones" }).click();
  await page.getByRole("button", { name: "Add milestone" }).first().click();
  const msDialog = page.getByRole("dialog");
  await msDialog.getByLabel("Title (required)").fill("Alpha release");
  await msDialog.getByLabel("Due date").fill(iso(new Date(today.getTime() + 14 * 86400000)));
  await msDialog.getByLabel("Deliverables").fill("Working login");
  await msDialog.getByRole("button", { name: "Save milestone" }).click();
  await expect(page.getByRole("heading", { name: "Alpha release" })).toBeVisible();

  // 4. Create a task linked to the workstream and milestone, then a subtask
  await page.locator("main").getByRole("button", { name: "New task" }).click();
  const taskDialog = page.getByRole("dialog");
  await taskDialog.getByLabel("Title (required)").fill("Build login");
  await choose(page, taskDialog, "Workstream", "E2E workstream");
  await choose(page, taskDialog, "Milestone", "Alpha release");
  await choose(page, taskDialog, "Priority", "High");
  await taskDialog.getByLabel("Estimated effort (hours)").fill("4");
  await taskDialog.getByLabel("Acceptance criteria").fill("A user can sign in");
  await taskDialog.getByRole("button", { name: "Create task" }).click();
  await expect(taskDialog).toBeHidden();

  await page.getByRole("tab", { name: "Board" }).click();
  await page.getByRole("button", { name: "Build login", exact: true }).click();
  const sheet = page.getByRole("dialog");
  await expect(sheet.getByRole("heading", { name: "Build login", exact: true })).toBeVisible();
  await sheet.getByRole("button", { name: "Add subtask" }).click();
  const subDialog = page.getByRole("dialog", { name: "New subtask" });
  await subDialog.getByLabel("Title (required)").fill("Write login tests");
  await subDialog.getByRole("button", { name: "Create task" }).click();
  await expect(sheet.getByRole("button", { name: /Write login tests/ })).toBeVisible();

  // 5. Schedule for today, 6. update status
  await sheet.getByLabel("Planned for").fill(TODAY);
  await choose(page, sheet, "Status", "In Progress");
  await expect(sheet.getByText(/Status To Do → In Progress/i)).toBeVisible();
  await page.keyboard.press("Escape");
  const inProgress = page.getByRole("listitem", { name: /In Progress column/ });
  await expect(inProgress.getByRole("button", { name: "Build login", exact: true })).toBeVisible();

  // The same task appears in the daily planner
  await page.goto("/planner");
  await expect(page.getByRole("button", { name: "Build login", exact: true })).toBeVisible();

  // 7. Record a daily update and 9. a research record
  await page.goto(`/projects/${projectId}`);
  for (const [kind, text] of [["Progress update", "Login form built"], ["Research", "Compared session vs token auth"]]) {
    await page.getByRole("button", { name: "Add update" }).click();
    const d = page.getByRole("dialog");
    await choose(page, d, "Type", kind);
    await d.getByLabel("What happened?").fill(text);
    await d.getByRole("button", { name: "Save update" }).click();
    await expect(d).toBeHidden();
  }
  await page.getByRole("tab", { name: "Decisions & updates" }).click();
  await expect(page.getByText("Compared session vs token auth")).toBeVisible();

  // 8. Generate a weekly report from real data
  await page.getByRole("tab", { name: "Reports" }).click();
  await choose(page, page.locator("main"), "Report", "Weekly report");
  await page.getByRole("button", { name: "Generate" }).click();
  const report = page.getByLabel("Report content (Markdown)");
  await expect(report).toHaveValue(/Build login/);
  await expect(report).toHaveValue(/Compared session vs token auth/);
  await expect(report).toHaveValue(/Tasks planned this week: \*\*1\*\*/);

  // 10. Create a reusable knowledge item linked to the project
  await page.goto("/knowledge");
  await page.getByRole("button", { name: "New item" }).first().click();
  const kd = page.getByRole("dialog");
  await kd.getByLabel("Title (required)").fill(`${RUN} auth research`);
  await kd.getByLabel("Research question").fill("Session or token authentication?");
  await kd.getByLabel("Findings").fill("Sessions are simpler for a single-origin app.");
  await choose(page, kd, "Origin project", PROJECT);
  await kd.getByRole("button", { name: "Save" }).click();
  await expect(page).toHaveURL(/\/knowledge\/[0-9a-f-]{36}$/);
  cleanupKnowledge.push(page.url().split("/").pop()!);
  await expect(page.getByRole("heading", { level: 1, name: `${RUN} auth research` })).toBeVisible();
  await expect(page.getByText("Research finding, not yet applied or tested in a project.")).toBeVisible();
  await expect(page.locator("main").getByText("Session or token authentication?")).toBeVisible();

  // 11–12. Records persist across a fresh browser session (server data, not client state)
  const fresh = await page.context().browser()!.newContext();
  const p2 = await fresh.newPage();
  await p2.goto(`/projects/${projectId}`);
  await expect(p2.getByRole("heading", { level: 1, name: PROJECT })).toBeVisible();
  await p2.getByRole("tab", { name: "Backlog" }).click();
  await expect(p2.getByRole("button", { name: /Build login/ })).toBeVisible();
  await expect(p2.getByRole("button", { name: /Write login tests/ })).toBeVisible();
  await p2.getByRole("tab", { name: "Library" }).click();
  await expect(p2.getByRole("link", { name: `${RUN} auth research` })).toBeVisible();
  await fresh.close();
});

test("failure scenarios are handled clearly", async ({ page, request }) => {
  // Unknown project shows a helpful error, not a crash
  await page.goto("/projects/00000000-0000-0000-0000-000000000000");
  await expect(page.getByRole("alert").filter({ hasText: "could not be loaded" })).toContainText("Project not found.");

  // Destructive delete needs the exact project name
  const created = await (await request.post("/api/projects", { data: { name: `${RUN} disposable` } })).json();
  await page.goto(`/projects/${created.id}`);
  await page.getByRole("button", { name: "Delete project" }).click();
  const confirm = page.getByRole("alertdialog");
  await expect(confirm.getByRole("button", { name: "Delete" })).toBeDisabled();
  await confirm.getByLabel(/Type .* to confirm/).fill(`${RUN} disposable`);
  await confirm.getByRole("button", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  expect((await request.get(`/api/projects/${created.id}`)).status()).toBe(404);
});
