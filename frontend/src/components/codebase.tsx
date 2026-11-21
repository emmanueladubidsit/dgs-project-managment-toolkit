"use client";
import { Bot, Copy, FolderGit2, GitCommitHorizontal, RefreshCw, Save, Unplug } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import {
  useClaudeSetup, useCodeEvents, useConnect, useConnection, useDisconnect, usePrivacyNames, useSaveEventAsUpdate,
  useSavePrivacyNames, useSyncNow,
} from "@/lib/queries-library";
import type { CodeEvent, Connection } from "@/lib/types";
import { EmptyState, QueryView, Section } from "./common";
import { ConfirmDialog } from "./confirm-dialog";
import { TextField } from "./form-fields";
import { PendingReview } from "./suggestions";

const copy = (t: string, what = "Copied.") => navigator.clipboard.writeText(t).then(() => toast.success(what), () => toast.error("Copy blocked — select the text and copy it."));

function ConnectForm({ projectId, current }: { projectId: string; current?: Connection }) {
  const [path, setPath] = useState(current?.path ?? "");
  const [claude, setClaude] = useState(current?.accept_claude ?? true);
  const [auto, setAuto] = useState(current?.auto_sync ?? true);
  const connect = useConnect(projectId);
  return (
    <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); connect.mutate({ path: path.trim(), accept_claude: claude, auto_sync: auto }); }}>
      <TextField label="Project folder (full path)" value={path} onChange={setPath} placeholder="/Users/you/Projects/my-app" hint="Tip: in Finder, select the folder and press ⌥⌘C to copy its path." />
      <label className="flex items-start gap-2 text-sm"><Checkbox checked={auto} onCheckedChange={(c) => setAuto(!!c)} className="mt-0.5" /> Check for new commits automatically every few minutes</label>
      <label className="flex items-start gap-2 text-sm"><Checkbox checked={claude} onCheckedChange={(c) => setClaude(!!c)} className="mt-0.5" /> Accept progress reports from Claude Code sessions in this folder (they wait for your approval)</label>
      <p className="text-xs text-muted-foreground">Read-only: the workspace runs read-only git commands (status, log) and never changes your files. It stores commit messages and changed file names — never source code, prompts, commands or author names.</p>
      <Button type="submit" disabled={!path.trim() || connect.isPending}><FolderGit2 /> {current ? "Update" : "Connect folder"}</Button>
    </form>
  );
}

function EventItem({ e }: { e: CodeEvent }) {
  const save = useSaveEventAsUpdate();
  const icon = e.kind === "commit" ? <GitCommitHorizontal className="size-4" aria-label="Commit" /> : e.kind === "files" ? <FolderGit2 className="size-4" aria-label="File changes" /> : <Bot className="size-4" aria-label="Claude Code" />;
  const label = { commit: "Commit", files: "Files changed", claude_session: "Claude Code session", claude_task: "Claude reported" }[e.kind];
  return (
    <li className="flex gap-3 py-2.5">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium break-words">{e.title}</p>
        <p className="text-xs text-muted-foreground">
          {label} · {formatDateTime(e.occurred_at)}
          {e.kind === "commit" && <> · <code>{e.ref.slice(0, 8)}</code>{e.detail.file_count ? ` · ${e.detail.file_count} file(s)` : ""}</>}
          {e.kind === "claude_session" && e.detail.turns ? ` · ${e.detail.turns} turn(s)${e.detail.ended ? " · ended" : ""}` : ""}
        </p>
        {e.summary && e.kind === "claude_session" && (
          <details className="mt-1 text-sm"><summary className="cursor-pointer text-xs text-primary">Latest summary from Claude</summary><p className="mt-1 whitespace-pre-wrap text-muted-foreground">{e.summary}</p></details>
        )}
        {e.detail.files && e.detail.files.length > 0 && (
          <details className="mt-1"><summary className="cursor-pointer text-xs text-muted-foreground">Files</summary>
            <ul className="mt-1 font-mono text-xs text-muted-foreground">{e.detail.files.slice(0, 20).map((f) => <li key={f} className="truncate">{f}</li>)}</ul></details>
        )}
      </div>
      {(e.kind === "claude_session" || e.kind === "commit") && (
        <Button size="xs" variant="ghost" className="shrink-0" onClick={() => save.mutate(e.id)}><Save /> Save as update</Button>
      )}
    </li>
  );
}

export function CodebasePanel({ projectId }: { projectId: string }) {
  const q = useConnection(projectId);
  const c = q.data ?? undefined;
  const events = useCodeEvents(projectId, !!c);
  const sync = useSyncNow(projectId);
  const disconnect = useDisconnect(projectId);
  return (
    <QueryView query={q}>
      {() => !c ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Section title="Connect the project's folder"><ConnectForm projectId={projectId} /></Section>
          <Section title="What this enables">
            <ul className="list-disc space-y-1 pl-5 text-sm">
              <li>See commits and uncommitted changes as they happen.</li>
              <li>Commits that mention a task (for example “Fix ISSUE-0001”) suggest marking it done.</li>
              <li>With Claude Code connected (<Link href="/admin" className="underline">Administration → Claude Code</Link>), session summaries and tasks Claude reports as done appear here for approval.</li>
            </ul>
          </Section>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <PendingReview projectId={projectId} title="Updates waiting for your review" />
            <Section title="Activity" actions={<Button size="sm" variant="outline" disabled={sync.isPending} onClick={() => sync.mutate(undefined)}><RefreshCw /> {sync.isPending ? "Syncing…" : "Sync now"}</Button>}>
              {(events.data ?? []).length === 0 ? <EmptyState title="No activity yet" description="Commits appear after the next sync; Claude Code sessions appear once Claude Code is connected." /> : (
                <ul className="divide-y">{(events.data ?? []).map((e) => <EventItem key={e.id} e={e} />)}</ul>
              )}
            </Section>
          </div>
          <div className="space-y-4">
            <Section title="Connected folder">
              <dl className="space-y-1.5 text-sm">
                <div><dt className="text-xs text-muted-foreground">Path</dt><dd className="font-mono text-xs break-all">{c.path}</dd></div>
                {!c.available && <p className="text-destructive">The folder is not available at this path.</p>}
                <div className="flex justify-between"><dt className="text-muted-foreground">Type</dt><dd>{c.is_git ? "Git repository" : "Folder (no git)"}</dd></div>
                {c.is_git && <div className="flex justify-between"><dt className="text-muted-foreground">Branch</dt><dd>{c.branch ?? "—"}</dd></div>}
                {c.is_git && <div className="flex justify-between"><dt className="text-muted-foreground">Uncommitted changes</dt><dd>{c.uncommitted_changes}</dd></div>}
                <div className="flex justify-between"><dt className="text-muted-foreground">Last synced</dt><dd>{c.last_synced_at ? formatDateTime(c.last_synced_at) : "—"}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Last activity</dt><dd>{c.last_activity_at ? formatDateTime(c.last_activity_at) : "—"}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Claude reports</dt><dd>{c.accept_claude ? "Accepted" : "Off"}</dd></div>
                {c.last_error && <p className="text-xs text-destructive">{c.last_error}</p>}
              </dl>
            </Section>
            <Section title="Change settings"><ConnectForm projectId={projectId} current={c} /></Section>
            <ConfirmDialog trigger={<Button variant="ghost" className="w-full"><Unplug /> Disconnect folder</Button>} confirmLabel="Disconnect"
              title="Disconnect this folder?" description="Stops watching it and removes its activity history from the workspace. Your files are not touched." onConfirm={() => disconnect.mutate(undefined)} />
          </div>
        </div>
      )}
    </QueryView>
  );
}

// ---------------------------------------------------------------- Administration
export function ClaudeSetupPanel() {
  const q = useClaudeSetup();
  const s = q.data;
  return (
    <Section title="Claude Code" className="md:col-span-2">
      {!s ? null : (
        <div className="space-y-4 text-sm">
          <p>Connect Claude Code so that sessions in your connected project folders can see each project&apos;s open tasks and report progress. Every report waits for your approval. Both steps use documented Claude Code features (MCP servers and hooks); the workspace does not read Claude&apos;s private session files.</p>
          <div>
            <p className="mb-1 font-medium">1. Register the workspace tools (once, for all projects) — run in a terminal:</p>
            <div className="flex gap-2"><code className="block flex-1 overflow-x-auto rounded-md bg-muted p-2 text-xs whitespace-nowrap">{s.mcp_command}</code>
              <Button size="sm" variant="outline" onClick={() => copy(s.mcp_command, "Command copied.")}><Copy /> Copy</Button></div>
            <p className="mt-1 text-xs text-muted-foreground">Claude can then call <code>list_open_tasks</code>, <code>report_task_progress</code> and <code>record_update</code>. To prompt it to report without being asked, add the text below to the project&apos;s CLAUDE.md.</p>
            <div className="mt-2 flex gap-2"><Textarea readOnly value={s.claude_md} rows={4} className="text-xs" aria-label="CLAUDE.md text" />
              <Button size="sm" variant="outline" onClick={() => copy(s.claude_md)}><Copy /> Copy</Button></div>
          </div>
          <div>
            <p className="mb-1 font-medium">2. Optional — automatic session summaries (hooks):</p>
            <p className="mb-1 text-xs text-muted-foreground">Merge this into the <code>hooks</code> section of <code>~/.claude/settings.json</code> (all projects) or a project&apos;s <code>.claude/settings.local.json</code>. At the end of each Claude turn and session it sends the summary (secrets redacted, names masked) and any task Claude marks complete to this workspace. It never blocks Claude: if the workspace is not running, nothing happens.</p>
            <div className="flex gap-2"><Textarea readOnly value={JSON.stringify(s.hook_settings, null, 2)} rows={8} className="font-mono text-xs" aria-label="Hook settings" />
              <Button size="sm" variant="outline" onClick={() => copy(JSON.stringify(s.hook_settings, null, 2))}><Copy /> Copy</Button></div>
          </div>
          <p className="text-xs text-muted-foreground">Then connect each project&apos;s folder on its <strong>Codebase</strong> tab. The commands contain a private workspace token that stops other local programs posting fake progress; keep it to yourself.</p>
        </div>
      )}
    </Section>
  );
}

export function PrivacyPanel() {
  const q = usePrivacyNames();
  const save = useSavePrivacyNames();
  const [rows, setRows] = useState<{ name: string; replacement: string }[] | null>(null);
  const list = rows ?? q.data ?? [];
  const set = (i: number, k: "name" | "replacement", v: string) => setRows(list.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  return (
    <Section title="Privacy — names to mask" className="md:col-span-2">
      <p className="mb-3 text-sm">Names listed here are replaced with a role wherever text enters or leaves the workspace: Claude Code reports, commit messages, AI prompts and exported documents. Secrets such as API keys and passwords are always redacted.</p>
      <ul className="space-y-2">
        {list.map((r, i) => (
          <li key={i} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <input className="h-8 rounded-lg border bg-transparent px-2.5 text-sm" value={r.name} onChange={(e) => set(i, "name", e.target.value)} placeholder="Full name" aria-label={`Name ${i + 1}`} />
            <input className="h-8 rounded-lg border bg-transparent px-2.5 text-sm" value={r.replacement} onChange={(e) => set(i, "replacement", e.target.value)} placeholder="Shown as, e.g. Reviewer" aria-label={`Replacement ${i + 1}`} />
            <Button size="sm" variant="ghost" onClick={() => setRows(list.filter((_, j) => j !== i))}>Remove</Button>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="outline" onClick={() => setRows([...list, { name: "", replacement: "a colleague" }])}>Add a name</Button>
        <Button size="sm" disabled={rows === null || save.isPending} onClick={() => save.mutate(list.filter((r) => r.name.trim().length >= 2), { onSuccess: () => setRows(null) })}>Save</Button>
      </div>
    </Section>
  );
}
