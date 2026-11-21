"use client";
import { ExternalLink, FileText, FolderOpen, Link2, Plus, StickyNote, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DOCUMENT_CATEGORY_LABEL, fileSize, formatDate, formatDateTime } from "@/lib/format";
import { useProjects, useTasks } from "@/lib/queries";
import {
  useCreateDocument, useDeleteDocument, useDocument, useDocumentAction, useDocumentRoots, useDocuments, usePreview,
  useRegisterFiles, useRegisterRoot, useRemoveRoot, useScan, useUpdateDocument,
} from "@/lib/queries-library";
import type { DocumentCategory, ProjectDocument, ScannedFile } from "@/lib/types";
import { cn } from "@/lib/utils";
import { EmptyState, ErrorState, LoadingState, QueryView, Section } from "./common";
import { ConfirmDialog } from "./confirm-dialog";
import { orNull, SelectField, TextAreaField, TextField } from "./form-fields";
import { useOpenTask } from "./task-sheet";

const CATEGORY_OPTIONS = Object.entries(DOCUMENT_CATEGORY_LABEL).map(([value, label]) => ({ value, label }));
const SOURCE_ICON = { file: FileText, link: Link2, note: StickyNote };
const SOURCE_LABEL = { file: "File in a registered folder", link: "External link", note: "Note in the workspace" };

export function AddDocumentDialog({ trigger, projectId }: { trigger: ReactNode; projectId?: string }) {
  const [open, setOpen] = useState(false);
  const fresh = () => ({ kind: "link", title: "", url: "", content: "", category: "other", project_id: projectId ?? null as string | null, description: "" });
  const [form, setForm] = useState(fresh);
  const projects = useProjects();
  const create = useCreateDocument();
  return (
    <Dialog open={open} onOpenChange={(o) => { if (o) setForm(fresh()); setOpen(o); }}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add a document</DialogTitle>
          <DialogDescription>Link to a document stored elsewhere, or write a short document here. To index files on this computer, register their folder in the Folders tab.</DialogDescription>
        </DialogHeader>
        <form id="add-doc" className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => {
          e.preventDefault();
          create.mutate({ title: form.title.trim(), category: form.category as DocumentCategory, project_id: form.project_id, description: orNull(form.description),
            url: form.kind === "link" ? form.url.trim() : null, content: form.kind === "note" ? orNull(form.content) : null }, { onSuccess: () => setOpen(false) });
        }}>
          <SelectField label="Type" value={form.kind} onChange={(v) => setForm({ ...form, kind: v ?? "link" })}
            options={[{ value: "link", label: "Link to a document" }, { value: "note", label: "Write it here" }]} />
          <SelectField label="Category" value={form.category} onChange={(v) => setForm({ ...form, category: v ?? "other" })} options={CATEGORY_OPTIONS} />
          <TextField label="Title" required value={form.title} onChange={(v) => setForm({ ...form, title: v })} className="sm:col-span-2" autoFocus />
          {form.kind === "link"
            ? <TextField label="Link (https://…)" type="url" required value={form.url} onChange={(v) => setForm({ ...form, url: v })} className="sm:col-span-2" />
            : <TextAreaField label="Content" value={form.content} onChange={(v) => setForm({ ...form, content: v })} rows={8} className="sm:col-span-2" />}
          <SelectField label="Project" value={form.project_id} onChange={(v) => setForm({ ...form, project_id: v })} noneLabel="No project" disabled={!!projectId}
            options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <TextField label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} />
        </form>
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button type="submit" form="add-doc" disabled={!form.title.trim() || (form.kind === "link" && !form.url.trim()) || create.isPending}>Add</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function DocumentTable({ docs, onOpen, showProject = true }: { docs: ProjectDocument[]; onOpen: (id: string) => void; showProject?: boolean }) {
  if (docs.length === 0) return <EmptyState title="No documents" description="Add links or notes, or register a project folder to index its files." />;
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-left text-xs text-muted-foreground">
          <tr><th className="px-3 py-2 font-medium">Document</th><th className="px-3 font-medium">Category</th>{showProject && <th className="px-3 font-medium">Project</th>}<th className="px-3 font-medium">Location</th><th className="px-3 font-medium">Updated</th></tr>
        </thead>
        <tbody>
          {docs.map((d) => {
            const Icon = SOURCE_ICON[d.source];
            return (
              <tr key={d.id} className="border-t">
                <td className="px-3 py-2">
                  <button className="flex items-center gap-2 text-left font-medium hover:underline" onClick={() => onOpen(d.id)}>
                    <Icon className="size-4 shrink-0 text-muted-foreground" aria-label={SOURCE_LABEL[d.source]} />{d.title}
                  </button>
                  {d.file_available === false && <span className="text-xs text-destructive">File not found at its registered location</span>}
                </td>
                <td className="px-3">{DOCUMENT_CATEGORY_LABEL[d.category]}</td>
                {showProject && <td className="px-3">{d.project_name ?? "—"}</td>}
                <td className="max-w-xs truncate px-3 text-xs text-muted-foreground" title={d.relative_path ?? d.url ?? ""}>
                  {d.source === "file" ? `${d.root_name}/${d.relative_path}` : d.source === "link" ? d.url : "Workspace note"}
                </td>
                <td className="px-3 text-xs whitespace-nowrap text-muted-foreground">{formatDate((d.file_modified_at ?? d.updated_at).slice(0, 10))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function DocumentSheet({ id, onClose }: { id: string | null; onClose: () => void }) {
  return (
    <Sheet open={!!id} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        {id && <DocumentPanel id={id} onClose={onClose} />}
      </SheetContent>
    </Sheet>
  );
}

function DocumentPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const q = useDocument(id);
  const [showPreview, setShowPreview] = useState(false);
  const preview = usePreview(id, showPreview);
  const update = useUpdateDocument();
  const act = useDocumentAction();
  const del = useDeleteDocument();
  const projects = useProjects();
  const tasks = useTasks({ sort: "updated" });
  const openTask = useOpenTask();
  if (q.isPending) return <div className="p-6"><SheetTitle className="sr-only">Loading</SheetTitle><LoadingState /></div>;
  if (!q.data) return <div className="p-6"><SheetTitle className="sr-only">Unavailable</SheetTitle><ErrorState error={q.error} /></div>;
  const d = q.data;
  const linked = new Set(d.tasks.map((t) => t.task_id));
  return (
    <div className="flex flex-col gap-5 p-6">
      <SheetHeader className="p-0">
        <p className="text-xs text-muted-foreground">{SOURCE_LABEL[d.source]}</p>
        <SheetTitle className="pr-8 text-lg">{d.title}</SheetTitle>
        <SheetDescription className="sr-only">Document details</SheetDescription>
      </SheetHeader>
      {d.source === "file" && (
        <div className="rounded-lg bg-muted/50 p-3 text-xs">
          <p className="font-mono break-all">{d.root_name}/{d.relative_path}</p>
          <p className="mt-1 text-muted-foreground">{fileSize(d.size_bytes)} · modified {d.file_modified_at ? formatDateTime(d.file_modified_at) : "—"} · read-only</p>
          {d.file_available === false && <p className="mt-1 text-destructive">The file is no longer at this location. Re-scan its folder after moving it.</p>}
        </div>
      )}
      {d.url && <a href={d.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-sm text-primary underline break-all"><ExternalLink className="size-4 shrink-0" />{d.url}</a>}
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Category" value={d.category} onChange={(v) => v && update.mutate({ id: d.id, category: v as DocumentCategory })} options={CATEGORY_OPTIONS} />
        <SelectField label="Status" value={d.status} onChange={(v) => v && update.mutate({ id: d.id, status: v as never })}
          options={[{ value: "draft", label: "Draft" }, { value: "final", label: "Final" }, { value: "superseded", label: "Superseded" }]} />
        <SelectField label="Project" value={d.project_id} onChange={(v) => update.mutate({ id: d.id, project_id: v })} noneLabel="No project" className="col-span-2"
          options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
      </div>
      {d.description && <p className="text-sm whitespace-pre-wrap">{d.description}</p>}
      {(d.source === "file" || d.source === "note") && (
        <div>
          {!showPreview ? <Button variant="outline" size="sm" onClick={() => setShowPreview(true)}>{d.source === "file" ? "Preview text" : "Show content"}</Button> : (
            preview.isPending ? <LoadingState rows={2} /> : preview.error ? <p className="text-sm text-muted-foreground">{(preview.error as Error).message}</p> : (
              <pre className="max-h-96 overflow-auto rounded-lg border bg-muted/30 p-3 text-xs whitespace-pre-wrap">{preview.data?.text || "(empty)"}</pre>
            )
          )}
        </div>
      )}
      <div>
        <h3 className="mb-2 text-sm font-semibold">Linked tasks</h3>
        {d.tasks.length === 0 ? <p className="mb-2 text-sm text-muted-foreground">None.</p> : (
          <ul className="mb-2 space-y-1">{d.tasks.map((t) => (
            <li key={t.task_id} className="flex items-center justify-between text-sm">
              <button className="hover:underline" onClick={() => openTask(t.task_id)}>{t.task_title}</button>
              <Button size="icon-xs" variant="ghost" aria-label={`Unlink ${t.task_title}`} onClick={() => act.mutate({ id: d.id, path: `/tasks/${t.task_id}`, method: "DELETE" })}><X /></Button>
            </li>))}</ul>
        )}
        <Select value="" onValueChange={(tid) => act.mutate({ id: d.id, path: "/tasks", body: { task_id: tid } })}>
          <SelectTrigger className="w-full" aria-label="Link a task"><SelectValue placeholder="Link a task…" /></SelectTrigger>
          <SelectContent>{(tasks.data ?? []).filter((t) => !linked.has(t.id) && (!d.project_id || t.project_id === d.project_id)).slice(0, 100).map((t) => <SelectItem key={t.id} value={t.id}>{t.title}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="flex gap-2 border-t pt-4">
        <Button variant="outline" onClick={() => act.mutate({ id: d.id, path: d.archived_at ? "/restore" : "/archive" })}>{d.archived_at ? "Restore" : "Archive"}</Button>
        <ConfirmDialog trigger={<Button variant="destructive"><Trash2 /> Remove record</Button>} confirmLabel="Remove"
          title="Remove this document record?" description={d.source === "file" ? "Only the workspace record is removed. The file on your computer is not touched." : "This removes the record from the workspace."}
          onConfirm={() => del.mutate(d.id, { onSuccess: onClose })} />
      </div>
    </div>
  );
}

export function FoldersPanel() {
  const roots = useDocumentRoots();
  const projects = useProjects();
  const register = useRegisterRoot();
  const remove = useRemoveRoot();
  const [form, setForm] = useState({ name: "", path: "", project_id: null as string | null });
  const [scanning, setScanning] = useState<string | null>(null);
  return (
    <div className="space-y-4">
      <Section title="Register a project folder">
        <p className="mb-3 text-sm text-muted-foreground">The workspace only <strong>reads</strong> registered folders. It never moves, edits or deletes your files. Hidden files, dependency folders and anything that looks like a secret (.env, keys, credentials) are always skipped. System folders and your whole home folder cannot be registered.</p>
        <form className="grid gap-3 sm:grid-cols-[1fr_2fr_1fr_auto] sm:items-end" onSubmit={(e) => {
          e.preventDefault();
          register.mutate({ name: form.name.trim(), path: form.path.trim(), project_id: form.project_id }, { onSuccess: () => setForm({ name: "", path: "", project_id: null }) });
        }}>
          <TextField label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="App docs" />
          <TextField label="Full folder path" value={form.path} onChange={(v) => setForm({ ...form, path: v })} placeholder="/Users/you/Projects/app/docs" />
          <SelectField label="Project" value={form.project_id} onChange={(v) => setForm({ ...form, project_id: v })} noneLabel="None" options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
          <Button type="submit" disabled={!form.name.trim() || !form.path.trim() || register.isPending}><FolderOpen /> Register</Button>
        </form>
        <p className="mt-2 text-xs text-muted-foreground">Tip: in Finder, select a folder and press ⌥⌘C to copy its full path.</p>
      </Section>
      <QueryView query={roots}>
        {(list) => list.length === 0 ? <EmptyState title="No folders registered" /> : (
          <ul className="space-y-3">
            {list.map((r) => (
              <li key={r.id} className="rounded-xl border bg-card p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold">{r.name} {r.project_name && <span className="text-sm font-normal text-muted-foreground">· {r.project_name}</span>}</p>
                    <p className="font-mono text-xs break-all text-muted-foreground">{r.path}</p>
                    <p className="text-xs text-muted-foreground">{r.document_count} indexed · {r.last_scanned_at ? `scanned ${formatDateTime(r.last_scanned_at)}` : "not scanned yet"}
                      {!r.available && <span className="text-destructive"> · folder not found</span>}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => setScanning(scanning === r.id ? null : r.id)} disabled={!r.available}>{scanning === r.id ? "Hide files" : "Scan and choose files"}</Button>
                    <ConfirmDialog trigger={<Button size="sm" variant="ghost">Remove</Button>} confirmLabel="Remove" title={`Stop indexing “${r.name}”?`}
                      description={`Removes the folder and its ${r.document_count} index record(s) from the workspace. Your files are not touched.`} onConfirm={() => remove.mutate(r.id)} />
                  </div>
                </div>
                {scanning === r.id && <ScanPicker rootId={r.id} projectId={r.project_id} />}
              </li>
            ))}
          </ul>
        )}
      </QueryView>
    </div>
  );
}

function ScanPicker({ rootId, projectId }: { rootId: string; projectId: string | null }) {
  const scan = useScan();
  const registerFiles = useRegisterFiles();
  const projects = useProjects();
  const [files, setFiles] = useState<ScannedFile[] | null>(null);
  const [note, setNote] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [project, setProject] = useState<string | null>(projectId);
  const { mutate } = scan;
  const run = useCallback(() => mutate(rootId, { onSuccess: (r) => {
    setFiles(r.files); setNote(r.skipped_note + (r.truncated ? " Only the first 5,000 files are shown." : "")); setSelected(new Set());
  } }), [mutate, rootId]);
  // Scan when opened, and again after files are indexed (files reset to null).
  useEffect(() => { if (files === null) run(); }, [files, run]);
  if (files === null) {
    return <div className="mt-3">{scan.isError ? <Button size="sm" onClick={run}>Retry scan</Button> : <LoadingState rows={3} />}</div>;
  }
  const fresh = files.filter((f) => !f.document_id);
  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs text-muted-foreground">{files.length} file(s) found, {fresh.length} not yet indexed. {note}</p>
      <div className="flex flex-wrap items-center gap-2">
        <Button size="xs" variant="outline" onClick={() => setSelected(new Set(fresh.map((f) => f.relative_path)))}>Select all new</Button>
        <Button size="xs" variant="ghost" onClick={() => setSelected(new Set())}>Clear</Button>
        <SelectField label="Assign to project" value={project} onChange={setProject} noneLabel="No project" className="w-56" options={(projects.data ?? []).map((p) => ({ value: p.id, label: p.name }))} />
        <Button size="sm" disabled={selected.size === 0 || registerFiles.isPending}
          onClick={() => registerFiles.mutate({ rootId, paths: [...selected], project_id: project }, { onSuccess: () => setFiles(null) })}>
          <Plus /> Index {selected.size} file(s)
        </Button>
      </div>
      <ul className="max-h-80 overflow-y-auto rounded-lg border text-sm">
        {files.map((f) => (
          <li key={f.relative_path} className={cn("flex items-center gap-2 border-b px-3 py-1.5 last:border-0", f.document_id && "text-muted-foreground")}>
            <Checkbox disabled={!!f.document_id} checked={!!f.document_id || selected.has(f.relative_path)} aria-label={`Select ${f.relative_path}`}
              onCheckedChange={(c) => setSelected((s) => { const n = new Set(s); if (c) n.add(f.relative_path); else n.delete(f.relative_path); return n; })} />
            <span className="min-w-0 flex-1 truncate font-mono text-xs">{f.relative_path}</span>
            <span className="text-xs">{f.document_id ? "Indexed" : DOCUMENT_CATEGORY_LABEL[f.suggested_category]}</span>
            <span className="w-16 text-right text-xs text-muted-foreground">{fileSize(f.size_bytes)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DocumentsList({ projectId }: { projectId?: string }) {
  const [category, setCategory] = useState("all");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const docs = useDocuments({ project_id: projectId, category: category === "all" ? undefined : [category], q: q || undefined });
  return (
    <>
      <div className="mb-3 flex flex-wrap gap-2">
        <Input className="w-full sm:w-64" placeholder="Search documents…" aria-label="Search documents" value={q} onChange={(e) => setQ(e.target.value)} />
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-52" aria-label="Category"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="all">All categories</SelectItem>{CATEGORY_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent>
        </Select>
        <AddDocumentDialog projectId={projectId} trigger={<Button className="ml-auto"><Plus /> Add link or note</Button>} />
      </div>
      <QueryView query={docs}>{(list) => <DocumentTable docs={list} onOpen={setOpen} showProject={!projectId} />}</QueryView>
      <DocumentSheet id={open} onClose={() => setOpen(null)} />
    </>
  );
}
