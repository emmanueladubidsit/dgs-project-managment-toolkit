import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { chromium, expect, test, type BrowserContext } from "@playwright/test";

// Loads the real extension (extension/) in Chromium and drives it on a stand-in ChatGPT page:
// tick an answer → Keep → stored as a note; code block → Add to file → preview → Write.
const EXT = path.resolve(__dirname, "..", "..", "extension");
const API = "http://localhost:8010/api";
const RUN = `E2E-ext ${Date.now()}`;
const FOLDER = path.join(__dirname, "_tmp_ext_project");
const PAGE = `<!doctype html><html><body><main>
  <div data-message-author-role="user">Plan the project</div>
  <div data-message-author-role="assistant"><p>Use FastAPI with PostgreSQL for the ${RUN} backend.</p></div>
  <div data-message-author-role="assistant"><p>Create <code>src/health.py</code>:</p>
    <pre><code class="language-python">def health():\n    return "ok"\n</code></pre></div>
</main></body></html>`;

let ctx: BrowserContext;
let projectId = "";
let token = "";

test.beforeAll(async ({ request }) => {
  rmSync(FOLDER, { recursive: true, force: true });
  mkdirSync(FOLDER);
  projectId = (await (await request.post(`${API}/projects`, { data: { name: `${RUN} project` } })).json()).id;
  expect((await request.put(`${API}/projects/${projectId}/connection`, { data: { path: FOLDER } })).ok()).toBeTruthy();
  token = (await (await request.get(`${API}/claude/setup`)).json()).token;
  await request.put(`${API}/claude/settings`, { data: { allow_file_writes: true } });
  ctx = await chromium.launchPersistentContext(path.join(os.tmpdir(), `dgs-ext-${Date.now()}`), {
    channel: "chromium",
    args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`],
  });
  let [sw] = ctx.serviceWorkers();
  sw ??= await ctx.waitForEvent("serviceworker");
  // Runs inside the extension's service worker, where `chrome` exists.
  await sw.evaluate((t) => (globalThis as unknown as { chrome: { storage: { local: { set: (v: object) => Promise<void> } } } })
    .chrome.storage.local.set({ base: "http://localhost:8010", token: t }), token);
  await ctx.route("https://chatgpt.com/**", (route) => route.fulfill({ contentType: "text/html", body: PAGE }));
});

test.afterAll(async ({ request }) => {
  await ctx?.close();
  await request.put(`${API}/claude/settings`, { data: { allow_file_writes: false } });
  await request.delete(`${API}/projects/${projectId}?confirm=${encodeURIComponent(`${RUN} project`)}`);
  rmSync(FOLDER, { recursive: true, force: true });
});

test("keep a ticked answer and add a code block to a file", async () => {
  const page = await ctx.newPage();
  await page.goto("https://chatgpt.com/c/test");
  const keepBoxes = page.getByRole("checkbox", { name: "Keep this answer" });
  await expect(keepBoxes).toHaveCount(2);
  await keepBoxes.first().check();

  const tray = page.locator("#dgs-keep-root");
  await expect(tray.getByText("Keep to DGS · 1 selected")).toBeVisible();
  await tray.getByLabel("Project", { exact: true }).selectOption({ label: `${RUN} project` });
  await tray.getByRole("button", { name: "Keep 1" }).click();
  await expect(tray.getByText("Kept in the workspace as a note.")).toBeVisible();

  const docs = await (await page.request.get(`${API}/documents?project_id=${projectId}`)).json();
  expect(docs).toHaveLength(1);
  const doc = await (await page.request.get(`${API}/documents/${docs[0].id}`)).json();
  expect(doc.content).toContain(`Use FastAPI with PostgreSQL for the ${RUN} backend.`);
  expect(doc.content).not.toContain("Keep"); // the extension's own buttons are not kept
  expect(doc.tags).toContain("ai-clip");

  await page.getByRole("button", { name: "Add to file" }).click();
  const dialog = tray.getByRole("dialog", { name: "Add code to a file" });
  await expect(dialog.getByLabel("File path")).toHaveValue("src/health.py"); // guessed from the text above
  await dialog.getByRole("button", { name: "Preview" }).click();
  await expect(dialog.getByText("This creates a new file: src/health.py")).toBeVisible();
  await expect(dialog.getByLabel("Preview of the change")).toContainText('+    return "ok"');
  await dialog.getByRole("button", { name: "Write file" }).click();
  await expect(dialog.getByText(/Created src\/health.py/)).toBeVisible();
  expect(readFileSync(path.join(FOLDER, "src", "health.py"), "utf8")).toBe('def health():\n    return "ok"\n');

  // Changing an existing file shows the before/after first.
  writeFileSync(path.join(FOLDER, "src", "health.py"), "old\n");
  await page.getByRole("button", { name: "Add to file" }).click();
  await dialog.getByRole("button", { name: "Preview" }).click();
  await expect(dialog.getByLabel("Preview of the change")).toContainText("-old");
  await expect(dialog.getByText(/replaces the contents of src\/health.py/)).toBeVisible();
});
