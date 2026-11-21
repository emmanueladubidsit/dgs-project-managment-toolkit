import { expect, test } from "@playwright/test";

// Methodologies, voice/writing suggestions, documents and search — against the running app.
const RUN = `E2E-lib ${Date.now()}`;
let projectId = "";
let noteId = "";

test.beforeAll(async ({ request }) => {
  projectId = (await (await request.post("/api/projects", { data: { name: `${RUN} project` } })).json()).id;
});

test.afterAll(async ({ request }) => {
  if (noteId) await request.delete(`/api/voice/notes/${noteId}`);
  const logs = await (await request.get(`/api/work-logs?project_id=${projectId}`)).json();
  for (const l of logs) await request.delete(`/api/work-logs/${l.id}`);
  const docs = await (await request.get(`/api/documents?project_id=${projectId}`)).json();
  for (const d of docs) await request.delete(`/api/documents/${d.id}`);
  await request.delete(`/api/projects/${projectId}?confirm=${encodeURIComponent(`${RUN} project`)}`);
});

test("adopt a starter methodology into a project", async ({ page }) => {
  await page.goto("/methodologies");
  await page.getByRole("link", { name: "Conducting software testing" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Conducting software testing" })).toBeVisible();
  await page.getByRole("button", { name: "Adopt into a project" }).click();
  const d = page.getByRole("dialog");
  await d.getByLabel("Project", { exact: true }).click();
  await page.getByRole("option", { name: `${RUN} project` }).click();
  await d.getByRole("button", { name: "Adopt" }).click();
  await expect(page.getByText(/Adopted: 3 milestone\(s\) and 5 task\(s\) created/)).toBeVisible();

  await page.goto(`/projects/${projectId}`);
  await page.getByRole("tab", { name: "Methodology" }).click();
  await expect(page.getByText("Mandatory deliverables:")).toContainText("0 of 1");
  await page.getByRole("combobox", { name: "Status of Testing strategy" }).click();
  await page.getByRole("option", { name: "Done" }).click();
  await expect(page.getByText("Mandatory deliverables:")).toContainText("1 of 1");
  await page.getByRole("tab", { name: "Backlog" }).click();
  await expect(page.getByRole("button", { name: /Write the testing strategy/ })).toBeVisible();
});

test("turn pasted notes into reviewed tasks without duplicates", async ({ page }) => {
  await page.goto("/voice");
  await page.getByLabel("Title").fill(`${RUN} stand-up`);
  await page.getByLabel("Project", { exact: true }).click();
  await page.getByRole("option", { name: `${RUN} project` }).click();
  await page.getByLabel("Text", { exact: true }).fill("um so we finished the login page. we need to write the release notes. we decided to ship on friday.");
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/voice\/[0-9a-f-]{36}$/);
  noteId = page.url().split("/").pop()!;

  await page.getByRole("button", { name: "Generate" }).click();
  await expect(page.getByLabel("Generated text")).toHaveValue(/^So we finished the login page\. We need to write the release notes\./);

  await page.getByRole("button", { name: "Find suggestions" }).click();
  await expect(page.getByLabel("Task title")).toHaveValue("Write the release notes");
  await page.getByRole("button", { name: "Create task" }).click();
  await expect(page.getByLabel("Task title")).toHaveCount(0);
  // Running it again must not create the same suggestion twice
  await page.getByRole("button", { name: "Find suggestions" }).click();
  await expect(page.getByText("No new suggestions found.")).toBeVisible();

  await page.goto(`/projects/${projectId}`);
  await page.getByRole("tab", { name: "Backlog" }).click();
  await expect(page.getByRole("button", { name: "Write the release notes", exact: true })).toBeVisible();
});

test("add a document link and find it with global search", async ({ page }) => {
  await page.goto(`/projects/${projectId}`);
  await page.getByRole("tab", { name: "Library" }).click();
  await page.getByRole("button", { name: "Add link or note" }).click();
  const d = page.getByRole("dialog");
  await d.getByLabel("Title (required)").fill(`${RUN} design file`);
  await d.getByLabel("Link (https://…) (required)").fill("https://example.com/design");
  await d.getByRole("button", { name: "Add" }).click();
  await expect(page.getByRole("button", { name: `${RUN} design file` })).toBeVisible();

  await page.keyboard.press("ControlOrMeta+k");
  await page.getByRole("dialog").getByLabel("Search").fill(RUN);
  await expect(page.getByRole("dialog").getByText("Documents")).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("button", { name: new RegExp(`${RUN} design file`) })).toBeVisible();
});
