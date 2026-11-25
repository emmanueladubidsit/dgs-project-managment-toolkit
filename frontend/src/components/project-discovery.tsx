"use client";
// Discover projects in the recommended projects folder, and start new ones there (ADR 0010).
import { Copy, FileText, FolderGit2, FolderSearch, FolderPlus, RefreshCw, Settings } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { formatDate } from "@/lib/format";
import { useAddDiscovered, useDiscovery, useProjectsFolder, useSaveProjectsFolder, useStartProject, useTrackerInstructions } from "@/lib/queries-library";
import { EmptyState, LoadingState, Section } from "./common";
import { TextAreaField, TextField } from "./form-fields";

/** "Discover projects": lists project folders in the projects folder that are not connected yet. */
export function DiscoverProjectsDialog() {
  const [open, setOpen] = useState(false);
  const q = useDiscovery(open);
  const add = useAddDiscovered();
  const [added, setAdded] = useState<Record<string, string>>({});
  const d = q.data;
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild><Button variant="outline"><FolderSearch /> Discover projects</Button></DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Discover projects</DialogTitle>
          <DialogDescription>
            Looks for project folders (a git repository, CLAUDE.md, a tracker, package.json or pyproject.toml) up to two levels
            inside your projects folder. Adding one creates the project and connects its folder read only.
          </DialogDescription>
        </DialogHeader>
        {q.isPending || (q.isFetching && !d) ? <LoadingState rows={3} /> : !d ? null : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <p className="min-w-0"><span className="text-muted-foreground">Projects folder: </span><span className="font-mono text-xs break-all">{d.root}</span></p>
              <Button size="sm" variant="ghost" onClick={() => q.refetch()} disabled={q.isFetching}><RefreshCw className={q.isFetching ? "animate-spin" : undefined} /> Refresh</Button>
            </div>
            {!d.exists ? (
              <EmptyState title="The projects folder does not exist yet" description="Create it in Administration → Projects folder, or start a new project."
                action={<Button asChild variant="outline"><Link href="/admin"><Settings /> Open Administration</Link></Button>} />
            ) : d.candidates.length === 0 ? (
              <EmptyState title="No new projects found" description={`${d.connected} project folder(s) here are already connected. New folders appear when they contain a git repository, CLAUDE.md or a tracker.`} />
            ) : (
              <ul className="space-y-2">
                {d.candidates.map((c) => (
                  <li key={c.path} className="flex flex-wrap items-center gap-3 rounded-lg border p-3">
                    <FolderGit2 className="size-5 shrink-0 text-muted-foreground" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{c.name}</p>
                      <p className="font-mono text-xs break-all text-muted-foreground">{c.relative_path}</p>
                      <p className="text-xs text-muted-foreground">
                        {c.is_git ? "Git repository" : "Folder"} · changed {formatDate(c.modified_at)} ·{" "}
                        {c.has_tracker ? <span className="text-success"><FileText className="inline size-3" /> tracker found</span> : "no tracker yet"}
                      </p>
                    </div>
                    {added[c.path] ? (
                      <Button size="sm" variant="outline" asChild><Link href={`/projects/${added[c.path]}`}>Open project</Link></Button>
                    ) : (
                      <Button size="sm" disabled={add.isPending} onClick={() => add.mutate({ path: c.path }, { onSuccess: (r) => setAdded((a) => ({ ...a, [c.path]: r.project_id })) })}>Add</Button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        <DialogFooter><Button variant="outline" onClick={() => setOpen(false)}>Close</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const folderFrom = (name: string) => name.replace(/[^A-Za-z0-9 ._-]/g, "").trim().replace(/\s+/g, "-");

/** "Start a new project": creates the folder in the projects folder with a tracker and CLAUDE.md. */
export function StartProjectDialog() {
  const [open, setOpen] = useState(false);
  const folder = useProjectsFolder();
  const start = useStartProject();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [created, setCreated] = useState<string | null>(null);
  const folderName = folderFrom(name);
  const root = folder.data?.root ?? "";
  const reset = (o: boolean) => { setOpen(o); if (!o) { setName(""); setDescription(""); setCreated(null); } };
  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogTrigger asChild><Button variant="outline"><FolderPlus /> Start a new project</Button></DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Start a new project</DialogTitle>
          <DialogDescription>
            Creates a folder in your projects folder with a starter tracker
            (docs/project-management/PROGRESS-AND-PLAN-…md) and a CLAUDE.md telling Claude Code how to keep it. Existing files are never overwritten.
          </DialogDescription>
        </DialogHeader>
        {created ? (
          <div className="space-y-2 text-sm">
            <p>The project and its folder are ready. Open the folder in Claude Code to start working; press <strong>Refresh tracker</strong> on the project&apos;s Tracker tab to pick up progress.</p>
            <Button asChild><Link href={`/projects/${created}`}>Open project</Link></Button>
          </div>
        ) : (
          <form id="start-project" className="space-y-3" onSubmit={(e) => {
            e.preventDefault();
            start.mutate({ name: name.trim(), description: description.trim() || undefined }, { onSuccess: (r) => setCreated(r.project_id) });
          }}>
            <TextField label="Project name" required value={name} onChange={setName} autoFocus />
            <TextAreaField label="Description" value={description} onChange={setDescription} rows={2} />
            <p className="text-xs text-muted-foreground">
              Folder: <span className="font-mono break-all">{root ? `${root}/${folderName || "…"}` : "set the projects folder in Administration"}</span>
              {folder.data && !folder.data.exists && <span className="block text-warning">The projects folder does not exist yet. Create it in Administration first.</span>}
            </p>
          </form>
        )}
        {!created && (
          <DialogFooter>
            <Button variant="outline" onClick={() => reset(false)}>Cancel</Button>
            <Button type="submit" form="start-project" disabled={start.isPending || !folderName || !folder.data?.exists}>{start.isPending ? "Creating…" : "Create project"}</Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

/** Administration: where technical projects live, and the tracker instructions for Claude Code. */
export function ProjectsFolderPanel() {
  const folder = useProjectsFolder();
  const save = useSaveProjectsFolder();
  const info = useTrackerInstructions();
  const [root, setRoot] = useState<string | null>(null);
  const value = root ?? folder.data?.root ?? "";
  const dirty = root !== null && root !== folder.data?.root;
  const copy = (t: string) => navigator.clipboard.writeText(t).then(() => toast.success("Instructions copied."), () => toast.error("Copy blocked — select the text and copy it."));
  return (
    <Section title="Projects folder" className="md:col-span-2">
      <p className="text-sm">
        Keep every technical project in one folder so it is easy to find and stays separate from non-technical work.
        <strong> Discover projects</strong> (on the Projects page) scans it, and <strong>Start a new project</strong> creates new project folders here.
      </p>
      {folder.isPending ? <LoadingState rows={1} /> : (
        <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); save.mutate({ root: value }, { onSuccess: () => setRoot(null) }); }}>
          <TextField label="Folder" value={value} onChange={setRoot} className="min-w-0 flex-1" />
          <Button type="submit" disabled={!dirty || save.isPending}>Save</Button>
          {folder.data && !folder.data.exists && !dirty && (
            <Button type="button" variant="outline" disabled={save.isPending} onClick={() => save.mutate({ root: value, create: true })}><FolderPlus /> Create folder</Button>
          )}
        </form>
      )}
      {folder.data && (
        <p className={`mt-1 text-xs ${folder.data.exists ? "text-muted-foreground" : "text-warning"}`}>
          {folder.data.exists ? "The folder exists." : "This folder does not exist yet. Create it to start using it."}
          {folder.data.source === "default" && " (Default from PROJECTS_ROOT in backend/.env until you save one here.)"}
        </p>
      )}
      <details className="mt-4">
        <summary className="cursor-pointer text-sm font-medium">Tracker instructions for Claude Code (for existing projects)</summary>
        <p className="mt-2 text-xs text-muted-foreground">
          New projects get these automatically. For an existing project, add this to its CLAUDE.md so Claude Code keeps
          {" "}{info.data?.tracker_dir ?? "docs/project-management"}/PROGRESS-AND-PLAN-YYYY-MM-DD.md in the format the Tracker tab reads.
          The workspace never edits your existing projects.
        </p>
        {info.data && (
          <>
            <pre className="mt-2 max-h-72 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap">{info.data.claude_md}</pre>
            <Button size="sm" variant="outline" className="mt-2" onClick={() => copy(info.data!.claude_md)}><Copy /> Copy instructions</Button>
          </>
        )}
      </details>
    </Section>
  );
}
