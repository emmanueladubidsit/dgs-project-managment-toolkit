# ADR 0011 — AI tools through a browser extension; confirmed file writes

- **Status:** Accepted · 25 November 2026 · amends ADR 0007 (AI without new costs) and ADR 0010 (writes)

## Context

The user wants to use free web AI tools (ChatGPT, Claude, Gemini, Copilot) signed in with their own
accounts, keep chosen answers in a project without copy-pasting, and send code from a chat into
files in the project folder. Embedding the tools in the web app is not possible: checked on
25 November 2026, `chatgpt.com` and `copilot.microsoft.com` send `X-Frame-Options: SAMEORIGIN`,
`gemini.google.com` sends `DENY`, and `claude.ai` sends `frame-ancestors 'self'`. Signing in with
Google does not give another app access to a consumer chat history, and reusing a browser session
to read it would breach the tools' terms. A desktop wrapper would hit Google's block on sign-in
inside embedded browsers.

## Decision

1. **A small Manifest V3 extension** (`extension/`, plain JavaScript, no build) runs only on the
   four tools' sites. It adds a **Keep** tick box to each answer, **Keep selection** for any
   selected text (works even when a site changes its markup), and **Keep code** / **Add to file**
   on code blocks. Its interface lives in a Shadow DOM and inserts page text only as text.
2. **Only what is kept is stored.** `POST /api/clips` saves a keep as a project note (in-app
   document, category research, tags `ai-clip` + tool, link back to the chat) or a progress
   update, optionally creating a new project. Text is privacy-cleaned. The chat itself stays in the
   AI tool's history. No AI keys or provider APIs are used.
3. **Token-protected.** The extension calls the workspace on localhost through its background
   worker, with the workspace token (`X-Workspace-Token`); the address must be localhost.
4. **File writes are confirmed and off by default.** `POST /projects/{id}/files/preview` returns a
   unified diff (or "new file"); `…/files/write` writes only when **Allow the browser extension to
   write files** is on (Administration) and the file's SHA-256 still matches the preview. Writes are
   confined to the project's connected folder (no `..`, absolute paths or symlink escapes), never touch
   secret-looking files, `.git` or dependency folders, are text-only up to 512 KB, atomic, and
   recorded as `file_written` activity. File content is written exactly as previewed (no privacy
   rewriting of code).

## Consequences

- Works with every sign-in method, voice and uploads, because the tools run in the normal browser.
- Site markup changes can hide the per-answer tick boxes; Keep selection and code-block buttons
  keep working. Selectors are listed at the top of `extension/content.js`.
- The workspace now writes in two user-initiated places: new project folders (ADR 0010) and
  previewed extension writes.
- Organisations must approve both the AI tool and the extension.
