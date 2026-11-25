# Keep to DGS Workspace (browser extension)

Use ChatGPT, Claude, Gemini or Copilot as usual. This extension adds:

- **Keep** tick boxes on answers, and **Keep selection** for any selected text, then a **Keep** bar:
  choose the project (or a new one) and save as a note (project Library) or a progress update.
- **Keep code** and **Add to file** on code blocks: choose the project and the path (guessed from
  the chat), **Preview** the new file or the before/after, then **Write file**.

Only what you keep is stored in the workspace; chats stay in the AI tool. See ADR 0011.

## Install (Chrome or Edge)

1. Check that your organisation allows the AI tool and this extension.
2. Open `chrome://extensions` (or `edge://extensions`), turn on **Developer mode**, **Load unpacked**
   and choose this `extension/` folder.
3. Click the extension's toolbar icon, paste the token from the workspace
   (**Administration → Browser extension → Copy token**) and press **Save and test**.
4. To use **Add to file**: connect the project's folder on its **Codebase** tab, and turn on
   **Allow the browser extension to write files** in Administration.

The workspace must be running (`make api`). The extension only talks to `localhost`.

## When a site changes

The answer selectors are at the top of `content.js` (`ANSWER_SELECTORS`). If tick boxes stop
appearing, **Keep selection** and the code-block buttons still work.
