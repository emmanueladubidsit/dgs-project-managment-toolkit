import { expect, test } from "@playwright/test";

// The AI assistant in copy-and-paste mode (no model needed), plus stakeholder exports.
const RUN = `E2E-ai ${Date.now()}`;
let projectId = "";
let previous: Record<string, unknown> = {};

test.beforeAll(async ({ request }) => {
  previous = await (await request.get("/api/ai/status")).json();
  await request.put("/api/ai/settings", { data: { provider: "manual" } });
  projectId = (await (await request.post("/api/projects", { data: { name: `${RUN} project`, objectives: "Launch the pilot" } })).json()).id;
  await request.post("/api/tasks", { data: { project_id: projectId, title: "Prepare pilot materials", status: "blocked" } });
});

test.afterAll(async ({ request }) => {
  await request.put("/api/ai/settings", { data: { provider: previous.provider ?? "disabled", preset: previous.preset ?? "ollama",
    base_url: previous.base_url ?? "", model: previous.model ?? "" } });
  await request.delete(`/api/projects/${projectId}?confirm=${encodeURIComponent(`${RUN} project`)}`);
});

test("ask a grounded question via copy and paste", async ({ page }) => {
  await page.goto("/assistant");
  await expect(page.getByText("Copy-and-paste mode")).toBeVisible();
  await page.getByLabel("Project", { exact: true }).click();
  await page.getByRole("option", { name: `${RUN} project` }).click();
  await page.getByRole("button", { name: "What is blocked or overdue, and why?" }).click();
  const dialog = page.getByRole("dialog", { name: "Run this in your AI chat" });
  await expect(dialog.getByLabel("Prompt to copy")).toHaveValue(/Prepare pilot materials \[blocked/);
  await expect(dialog.getByLabel("Prompt to copy")).toHaveValue(/British English/);
  await dialog.getByLabel("Paste the AI answer").fill("“Prepare pilot materials” is blocked; no reason is stated in the workspace.");
  await dialog.getByRole("button", { name: "Use this answer" }).click();
  await expect(page.getByText("no reason is stated in the workspace")).toBeVisible();
  await expect(page.getByText(/Context used: \d+ workspace record/)).toBeVisible();
});

test("turn notes into reviewed tasks with AI", async ({ page }) => {
  await page.goto("/assistant");
  await page.getByRole("tab", { name: "Notes → tasks" }).click();
  await page.getByLabel("Project", { exact: true }).click();
  await page.getByRole("option", { name: `${RUN} project` }).click();
  await page.getByLabel("Text", { exact: true }).fill("We still need someone to book the venue for the pilot.");
  await page.getByRole("button", { name: "Suggest tasks and updates" }).click();
  const dialog = page.getByRole("dialog", { name: "Run this in your AI chat" });
  await dialog.getByLabel("Paste the AI answer").fill(JSON.stringify([
    { kind: "task", title: "Book the pilot venue", priority: "high", estimate_hours: 1, acceptance_criteria: "Venue confirmed in writing", evidence: "book the venue" },
  ]));
  await dialog.getByRole("button", { name: "Use this answer" }).click();
  await expect(page.getByLabel("Task title")).toHaveValue("Book the pilot venue");
  await expect(page.getByText("suggested by AI")).toBeVisible();
  await page.getByRole("button", { name: "Create task" }).click();
  await expect(page.getByLabel("Task title")).toHaveCount(0);
  const tasks = await (await page.request.get(`/api/tasks?project_id=${projectId}`)).json();
  const created = tasks.find((t: { title: string }) => t.title === "Book the pilot venue");
  expect(created.acceptance_criteria).toBe("Venue confirmed in writing");
  expect(created.priority).toBe("high");
});

test("download a stakeholder status deck", async ({ page }) => {
  await page.goto(`/projects/${projectId}`);
  await page.getByRole("button", { name: "Export" }).click();
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("menuitem", { name: "Slides (PowerPoint)" }).click()]);
  expect(download.suggestedFilename()).toMatch(/status-update\.pptx$/);
  const size = (await download.createReadStream()).readableLength;
  expect(size).toBeGreaterThanOrEqual(0);
  const r = await page.request.get(`/api/export/project/${projectId}/status?format=pptx`);
  expect(r.headers()["content-type"]).toContain("presentationml");
  expect((await r.body()).length).toBeGreaterThan(20000);
});
