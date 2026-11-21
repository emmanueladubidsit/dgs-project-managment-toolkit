import { execFileSync } from "node:child_process";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

// Connect a real (temporary) git repository and turn a commit into an approved task update.
const RUN = `E2E-code ${Date.now()}`;
const REPO = path.join(__dirname, "_tmp_repo");
const git = (...a: string[]) => execFileSync("git", ["-c", "user.name=Test Person", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false", "-C", REPO, ...a]);
let projectId = "";
let taskId = "";

test.beforeAll(async ({ request }) => {
  rmSync(REPO, { recursive: true, force: true });
  mkdirSync(REPO);
  execFileSync("git", ["-C", REPO, "init", "-q", "-b", "main"]);
  writeFileSync(path.join(REPO, "README.md"), "hello");
  git("add", "-A"); git("commit", "-qm", "Initial commit");
  projectId = (await (await request.post("/api/projects", { data: { name: `${RUN} project` } })).json()).id;
  taskId = (await (await request.post("/api/tasks", { data: { project_id: projectId, title: "DEMO-42: add a health check" } })).json()).id;
});

test.afterAll(async ({ request }) => {
  await request.delete(`/api/projects/${projectId}?confirm=${encodeURIComponent(`${RUN} project`)}`);
  rmSync(REPO, { recursive: true, force: true });
});

test("connect a folder, sync a commit and apply the suggested task update", async ({ page }) => {
  await page.goto(`/projects/${projectId}`);
  await page.getByRole("tab", { name: "Codebase" }).click();
  await page.getByLabel("Project folder (full path)").fill(REPO);
  await page.getByRole("button", { name: "Connect folder" }).click();
  await expect(page.getByText("Git repository")).toBeVisible();
  await expect(page.getByText("Initial commit")).toBeVisible();
  await expect(page.getByText("Test Person")).toHaveCount(0); // author names are not stored

  writeFileSync(path.join(REPO, "health.py"), "ok");
  git("add", "-A"); git("commit", "-qm", "Implement DEMO-42 health check endpoint");
  await page.getByRole("button", { name: "Sync now" }).click();
  await expect(page.getByText("Implement DEMO-42 health check endpoint", { exact: true })).toBeVisible();
  const review = page.getByText(/Updates waiting for your review/);
  await expect(review).toBeVisible();
  await expect(page.getByText("from a commit")).toBeVisible();
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(review).toHaveCount(0);
  const task = await (await page.request.get(`/api/tasks/${taskId}`)).json();
  expect(task.status).toBe("completed");
});
