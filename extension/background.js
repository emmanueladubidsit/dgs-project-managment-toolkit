// Calls the local workspace API on behalf of the page script. Only the workspace address and
// token from the options page are used; nothing is sent anywhere else.
const DEFAULTS = { base: "http://localhost:8010", token: "" };

async function settings() {
  const s = await chrome.storage.local.get(DEFAULTS);
  return { base: (s.base || DEFAULTS.base).replace(/\/+$/, ""), token: s.token || "" };
}

async function call({ method = "GET", path, body }) {
  const { base, token } = await settings();
  if (!/^http:\/\/(localhost|127\.0\.0\.1):\d+$/.test(base)) {
    return { ok: false, status: 0, error: "The workspace address must be on this computer (localhost)." };
  }
  if (!token) return { ok: false, status: 0, error: "Add your workspace token in the extension settings first." };
  try {
    const res = await fetch(`${base}/api${path}`, {
      method,
      headers: { "Content-Type": "application/json", "X-Workspace-Token": token },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) return { ok: false, status: res.status, error: data?.error?.message || `Request failed (${res.status}).`, code: data?.error?.code };
    return { ok: true, status: res.status, data };
  } catch {
    return { ok: false, status: 0, error: "Cannot reach the workspace. Is it running (make api)?" };
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg?.type === "dgs-api") {
    call(msg).then(reply);
    return true; // async reply
  }
  if (msg?.type === "dgs-options") {
    chrome.runtime.openOptionsPage();
  }
  return false;
});
