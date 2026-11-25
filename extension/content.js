// Keep to DGS Workspace — adds "Keep" tick boxes to AI answers and "Add to file" to code blocks.
// Nothing is sent until you press Keep or Write. Page text is only ever inserted as text.
(() => {
  if (window.__dgsKeep) return;
  window.__dgsKeep = true;

  const HOST = location.hostname;
  const TOOL = HOST.includes("chatgpt") ? "chatgpt" : HOST.includes("claude") ? "claude"
    : HOST.includes("gemini") ? "gemini" : HOST.includes("copilot") ? "copilot" : "other";
  // Assistant answers per site. Sites change their markup; "Keep selection" always works.
  const ANSWER_SELECTORS = {
    chatgpt: ['[data-message-author-role="assistant"]'],
    claude: ['[data-testid="assistant-message"]', ".font-claude-response", ".font-claude-message"],
    gemini: ["model-response", "message-content"],
    copilot: ['[data-content="ai-message"]', '[class*="ai-message"]'],
    other: ['[data-message-author-role="assistant"]'],
  }[TOOL];
  // A file path such as src/app.py or README.md (extension starts with a letter, so "v1.1" is not one).
  const PATH_RE = /(?:^|[\s`"'(*])((?:[\w.-]+\/)*[\w-][\w.-]*\.[A-Za-z][A-Za-z0-9]{0,9})(?=$|[\s`"'):*,.])/g;

  const api = (path, method = "GET", body) => chrome.runtime.sendMessage({ type: "dgs-api", path, method, body });
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "on") for (const [ev, fn] of Object.entries(v)) n.addEventListener(ev, fn);
      else if (k === "text") n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const kid of kids) if (kid) n.append(kid);
    return n;
  };

  // ------------------------------------------------------------ UI root (Shadow DOM)
  const host = el("div", { id: "dgs-keep-root" });
  host.style.cssText = "position:fixed;z-index:2147483647;right:16px;bottom:16px;";
  const root = host.attachShadow({ mode: "open" });
  root.append(el("style", { text: `
    :host { all: initial; }
    * { box-sizing: border-box; font: 13px/1.4 system-ui, -apple-system, sans-serif; }
    .card { background: #fff; color: #1f2328; border: 1px solid #d0d7de; border-radius: 10px; box-shadow: 0 6px 24px rgba(0,0,0,.18); padding: 10px; width: 320px; }
    .pill { background: #1d4ed8; color: #fff; border: 0; border-radius: 999px; padding: 6px 12px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,.2); }
    .row { display: flex; gap: 6px; align-items: center; margin-top: 8px; }
    select, input { width: 100%; padding: 5px 6px; border: 1px solid #c8ccd1; border-radius: 6px; background: #fff; color: #1f2328; }
    button.b { padding: 5px 10px; border-radius: 6px; border: 1px solid #c8ccd1; background: #f6f8fa; color: #1f2328; cursor: pointer; }
    button.p { background: #1d4ed8; border-color: #1d4ed8; color: #fff; font-weight: 600; }
    button:disabled { opacity: .5; cursor: default; }
    .muted { color: #57606a; font-size: 12px; }
    .err { color: #cf222e; font-size: 12px; } .ok { color: #1a7f37; font-size: 12px; }
    .modal { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; }
    .dialog { width: min(760px, 92vw); max-height: 86vh; overflow: auto; }
    pre.diff { background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 8px; max-height: 50vh; overflow: auto; white-space: pre; font: 12px/1.4 ui-monospace, Menlo, monospace; }
    .add { color: #1a7f37; } .del { color: #cf222e; } .hunk { color: #8250df; }
    h3 { margin: 0 0 4px; font-size: 14px; font-weight: 700; }
  ` }));
  document.documentElement.append(host);

  const state = { items: [], projects: null, writes: false };

  async function loadProjects(force = false) {
    if (state.projects && !force) return state.projects;
    const r = await api("/clips/projects");
    if (!r.ok) throw new Error(r.error);
    state.projects = r.data.projects;
    state.writes = r.data.file_writes_allowed;
    return state.projects;
  }

  function projectSelect(onlyWithFolder) {
    const sel = el("select", { "aria-label": "Project" });
    loadProjects().then((ps) => {
      const list = onlyWithFolder ? ps.filter((p) => p.has_folder) : ps;
      if (!list.length) sel.append(el("option", { value: "", text: onlyWithFolder ? "No project has a connected folder" : "No projects yet" }));
      for (const p of list) sel.append(el("option", { value: p.id, text: p.name }));
      if (!onlyWithFolder) sel.append(el("option", { value: "__new__", text: "+ New project…" }));
      const last = sessionStorage.getItem("dgs-last-project");
      if (last && list.some((p) => p.id === last)) sel.value = last;
      sel.dispatchEvent(new Event("change"));
    }, (e) => sel.append(el("option", { value: "", text: e.message })));
    return sel;
  }

  // ------------------------------------------------------------ Keep tray
  function render() {
    root.querySelectorAll(".tray").forEach((n) => n.remove());
    const tray = el("div", { class: "tray" });
    if (!state.items.length) {
      tray.append(el("button", { class: "pill", title: "Keep to DGS: tick answers or select text", text: "DGS",
        on: { click: () => chrome.runtime.sendMessage({ type: "dgs-options" }) } }));
      root.append(tray);
      return;
    }
    const status = el("div", { class: "muted", role: "status" });
    const sel = projectSelect(false);
    const newName = el("input", { placeholder: "New project name", "aria-label": "New project name" });
    newName.style.display = "none";
    sel.addEventListener("change", () => { newName.style.display = sel.value === "__new__" ? "" : "none"; });
    const saveAs = el("select", { "aria-label": "Save as" },
      el("option", { value: "note", text: "Save as a note (Library)" }),
      el("option", { value: "update", text: "Save as a progress update" }));
    const title = el("input", { placeholder: "Title (optional)", "aria-label": "Title" });
    const keep = el("button", { class: "b p", text: `Keep ${state.items.length}` });
    keep.addEventListener("click", async () => {
      const body = { save_as: saveAs.value, title: title.value.trim() || undefined, items: state.items.map(({ node, ...i }) => i) };
      if (sel.value === "__new__") {
        if (!newName.value.trim()) { status.className = "err"; status.textContent = "Enter a name for the new project."; return; }
        body.new_project_name = newName.value.trim();
      } else if (sel.value) body.project_id = sel.value;
      else { status.className = "err"; status.textContent = "Choose a project."; return; }
      keep.disabled = true;
      const r = await api("/clips", "POST", body);
      keep.disabled = false;
      if (!r.ok) { status.className = "err"; status.textContent = r.error; return; }
      sessionStorage.setItem("dgs-last-project", r.data.project_id);
      if (r.data.created_project) state.projects = null;
      clearAll();
      flash(`Kept in the workspace as ${r.data.saved_as === "note" ? "a note" : "a progress update"}.`);
    });
    tray.append(el("div", { class: "card" },
      el("h3", { text: `Keep to DGS · ${state.items.length} selected` }),
      el("div", { class: "muted", text: "Only what you keep is stored. Your chat stays in " + (TOOL === "other" ? "the AI tool" : TOOL) + "." }),
      el("div", { class: "row" }, sel), el("div", { class: "row" }, newName),
      el("div", { class: "row" }, saveAs), el("div", { class: "row" }, title),
      el("div", { class: "row" }, keep, el("button", { class: "b", text: "Clear", on: { click: clearAll } })),
      status));
    root.append(tray);
  }

  function flash(text, cls = "ok") {
    const n = el("div", { class: "card " }, el("div", { class: cls, text }));
    n.classList.add("tray");
    root.querySelectorAll(".tray").forEach((x) => x.remove());
    root.append(n);
    setTimeout(render, 2500);
  }

  function clearAll() {
    for (const i of state.items) if (i.node?.__dgsBox) i.node.__dgsBox.checked = false;
    state.items = [];
    render();
  }

  // The answer's visible text, without the extension's own buttons.
  function textOf(node) {
    const ui = [...node.querySelectorAll("[data-dgs-ui]")];
    ui.forEach((u) => { u.dataset.dgsDisplay = u.style.display; u.style.display = "none"; });
    const text = node.innerText.trim();
    ui.forEach((u) => { u.style.display = u.dataset.dgsDisplay || ""; });
    return text;
  }

  function toggle(node, on) {
    state.items = state.items.filter((i) => i.node !== node);
    if (on) state.items.push({ node, text: textOf(node), kind: "answer", tool: TOOL, url: location.href });
    render();
  }

  // ------------------------------------------------------------ decorate the page
  function decorateAnswers() {
    for (const sel of ANSWER_SELECTORS) {
      for (const node of document.querySelectorAll(sel)) {
        if (node.__dgsBox?.isConnected || node.closest("[data-dgs-answer]") !== node && node.closest("[data-dgs-answer]")) continue;
        node.setAttribute("data-dgs-answer", "1");
        const box = el("input", { type: "checkbox", title: "Keep this answer in the DGS workspace", "aria-label": "Keep this answer" });
        box.addEventListener("change", () => toggle(node, box.checked));
        const wrap = el("label", { "data-dgs-ui": "1" }, box, el("span", { text: " Keep" }));
        wrap.style.cssText = "display:inline-flex;align-items:center;gap:4px;font:12px system-ui,sans-serif;color:#57606a;cursor:pointer;margin:4px 0;user-select:none;";
        node.__dgsBox = box;
        node.prepend(wrap);
      }
    }
  }

  function codeOf(pre) {
    const code = pre.querySelector("code") || pre;
    const lang = (code.className.match(/language-([\w+#-]+)/) || [])[1] || null;
    return { text: code.innerText.replace(/\n$/, ""), language: lang };
  }

  function pathIn(text) {
    const hits = [...(text || "").matchAll(PATH_RE)].map((m) => m[1]);
    return hits.reverse().find((h) => h.includes("/")) || hits[0] || ""; // nearest, prefer folders
  }

  function guessPath(pre, text) {
    const first = text.split("\n", 1)[0];
    const m = first.match(/^\s*(?:\/\/|#|--|\/\*|<!--|;)\s*(?:file(?:name)?:\s*)?((?:[\w.-]+\/)*[\w-][\w.-]*\.[A-Za-z][A-Za-z0-9]{0,9})/i);
    if (m) return m[1];
    // The text just before the code block, walking out from it (sites wrap code in containers).
    let node = pre;
    for (let depth = 0; node && depth < 4; depth++) {
      let prev = node.previousElementSibling;
      for (let i = 0; prev && i < 2; i++, prev = prev.previousElementSibling) {
        if (prev.matches("[data-dgs-ui]")) { i--; continue; }
        const hit = pathIn(prev.innerText);
        if (hit) return hit;
      }
      if (node.matches?.("[data-dgs-answer]")) break;
      node = node.parentElement;
    }
    return "";
  }

  function decorateCode() {
    for (const pre of document.querySelectorAll("pre")) {
      if (pre.__dgsCode?.isConnected || pre.closest("#dgs-keep-root")) continue;
      const btn = el("button", { type: "button", "data-dgs-ui": "1", title: "Add this code to a file in a project folder", text: "Add to file" });
      btn.style.cssText = "font:12px system-ui,sans-serif;padding:2px 8px;margin:4px 6px 4px 0;border:1px solid #c8ccd1;border-radius:6px;background:#f6f8fa;color:#1f2328;cursor:pointer;";
      btn.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); openFileDialog(pre); });
      const keep = el("button", { type: "button", "data-dgs-ui": "1", title: "Keep this code block", text: "Keep code" });
      keep.style.cssText = btn.style.cssText;
      keep.addEventListener("click", (e) => {
        e.preventDefault(); e.stopPropagation();
        const c = codeOf(pre);
        state.items.push({ text: c.text, kind: "code", language: c.language || undefined, tool: TOOL, url: location.href });
        render();
      });
      const bar = el("div", { "data-dgs-ui": "1" }, btn, keep);
      pre.__dgsCode = bar;
      pre.after(bar);
    }
  }

  // ------------------------------------------------------------ Add to file
  function openFileDialog(pre) {
    const { text, language } = codeOf(pre);
    const status = el("div", { role: "status" });
    const sel = projectSelect(true);
    const path = el("input", { value: guessPath(pre, text), placeholder: "path/inside/project.py", "aria-label": "File path" });
    const diffBox = el("pre", { class: "diff", "aria-label": "Preview of the change" });
    diffBox.style.display = "none";
    let previewed = null;
    const write = el("button", { class: "b p", text: "Write file", disabled: "true" });
    const previewBtn = el("button", { class: "b", text: "Preview" });
    const close = () => modal.remove();
    const resetPreview = () => { previewed = null; write.disabled = true; };
    path.addEventListener("input", resetPreview);
    sel.addEventListener("change", resetPreview);

    previewBtn.addEventListener("click", async () => {
      status.className = "muted"; status.textContent = "Preparing preview…";
      if (!sel.value) { status.className = "err"; status.textContent = "Connect a project folder in the workspace (Codebase tab) first."; return; }
      const r = await api(`/projects/${sel.value}/files/preview`, "POST", { path: path.value.trim(), content: text.endsWith("\n") ? text : text + "\n" });
      if (!r.ok) { status.className = "err"; status.textContent = r.error; diffBox.style.display = "none"; return; }
      const p = r.data;
      previewed = { project: sel.value, path: p.path, sha: p.current_sha256 };
      diffBox.replaceChildren();
      for (const line of p.diff.split("\n")) {
        const cls = line.startsWith("+") && !line.startsWith("+++") ? "add" : line.startsWith("-") && !line.startsWith("---") ? "del" : line.startsWith("@@") ? "hunk" : "";
        diffBox.append(el("span", { class: cls, text: line + "\n" }));
      }
      diffBox.style.display = p.unchanged ? "none" : "";
      status.className = p.writes_allowed ? "muted" : "err";
      status.textContent = p.unchanged ? "The file already contains exactly this code." :
        !p.writes_allowed ? "Writing files is switched off. Enable it in the workspace: Administration → Browser extension." :
        p.will_create ? `This creates a new file: ${p.path}` : `This replaces the contents of ${p.path} (see the changes above).`;
      write.disabled = p.unchanged || !p.writes_allowed;
    });

    write.addEventListener("click", async () => {
      if (!previewed) return;
      write.disabled = true;
      const r = await api(`/projects/${previewed.project}/files/write`, "POST", {
        path: previewed.path, content: text.endsWith("\n") ? text : text + "\n", expected_sha256: previewed.sha,
      });
      if (!r.ok) { status.className = "err"; status.textContent = r.error; return; }
      status.className = "ok";
      status.textContent = `${r.data.created ? "Created" : "Updated"} ${r.data.path} (${r.data.bytes} bytes).`;
      setTimeout(close, 1500);
    });

    const modal = el("div", { class: "modal", on: { click: (e) => { if (e.target === modal) close(); } } },
      el("div", { class: "card dialog", role: "dialog", "aria-label": "Add code to a file" },
        el("h3", { text: "Add code to a project file" }),
        el("div", { class: "muted", text: `${language ? language + " · " : ""}${text.split("\n").length} line(s). Nothing is written until you press Write file.` }),
        el("div", { class: "row" }, sel), el("div", { class: "row" }, path),
        el("div", { class: "row" }, previewBtn, write, el("button", { class: "b", text: "Cancel", on: { click: close } })),
        status, diffBox));
    root.append(modal);
    path.focus();
  }

  // ------------------------------------------------------------ Keep selection
  const selBtn = el("button", { class: "pill", text: "Keep selection" });
  selBtn.style.cssText = "position:fixed;display:none;";
  root.append(selBtn);
  let selected = "";
  document.addEventListener("mouseup", (e) => {
    if (e.composedPath().includes(host)) return;
    setTimeout(() => {
      const s = window.getSelection();
      selected = s ? s.toString().trim() : "";
      if (selected.length < 15 || !s.rangeCount) { selBtn.style.display = "none"; return; }
      const rect = s.getRangeAt(0).getBoundingClientRect();
      selBtn.style.cssText = `position:fixed;left:${Math.max(8, rect.left)}px;top:${Math.max(8, rect.bottom + 6)}px;`;
    }, 0);
  });
  selBtn.addEventListener("click", () => {
    if (selected) state.items.push({ text: selected, kind: "selection", tool: TOOL, url: location.href });
    selBtn.style.display = "none";
    window.getSelection()?.removeAllRanges();
    render();
  });

  // ------------------------------------------------------------ keep decorating as the chat grows
  let pending = false;
  const decorate = () => { pending = false; decorateAnswers(); decorateCode(); };
  new MutationObserver((muts) => {
    if (pending || muts.every((m) => [...m.addedNodes].every((n) => n.nodeType === 1 && n.closest?.("[data-dgs-ui]")))) return;
    pending = true;
    setTimeout(decorate, 600);
  }).observe(document.body, { childList: true, subtree: true });
  decorate();
  render();
})();
