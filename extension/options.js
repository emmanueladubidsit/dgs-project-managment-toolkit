const $ = (id) => document.getElementById(id);
chrome.storage.local.get({ base: "http://localhost:8010", token: "" }).then((s) => {
  $("base").value = s.base;
  $("token").value = s.token;
});
$("save").addEventListener("click", async () => {
  await chrome.storage.local.set({ base: $("base").value.trim() || "http://localhost:8010", token: $("token").value.trim() });
  const r = await chrome.runtime.sendMessage({ type: "dgs-api", path: "/clips/projects" });
  $("status").textContent = r.ok
    ? `Connected: ${r.data.projects.length} project(s). File writes are ${r.data.file_writes_allowed ? "allowed" : "off (enable in Administration)"}.`
    : r.error;
  $("status").style.color = r.ok ? "#1a7f37" : "#cf222e";
});
