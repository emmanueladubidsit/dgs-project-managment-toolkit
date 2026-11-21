"use client";
import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useSearch } from "@/lib/queries-library";
import type { SearchHit } from "@/lib/types";
import { useOpenTask } from "./task-sheet";

const TYPE_LABEL: Record<SearchHit["type"], string> = {
  project: "Projects", task: "Tasks", knowledge: "Knowledge & research", methodology: "Methodologies",
  document: "Documents", work_log: "Updates", voice_note: "Voice & writing notes",
};

function useDebounced(value: string, ms = 250) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

/** Search everything (⌘K / Ctrl+K). */
export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const debounced = useDebounced(q);
  const results = useSearch(debounced);
  const router = useRouter();
  const openTask = useOpenTask();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function go(h: SearchHit) {
    setOpen(false);
    if (h.type === "task") return openTask(h.id);
    const href = { project: `/projects/${h.id}`, knowledge: `/knowledge/${h.id}`, methodology: `/methodologies/${h.id}`,
      document: "/documents", work_log: h.project_id ? `/projects/${h.project_id}` : "/planner", voice_note: `/voice/${h.id}` }[h.type];
    router.push(href);
  }

  const groups = new Map<SearchHit["type"], SearchHit[]>();
  for (const h of results.data ?? []) groups.set(h.type, [...(groups.get(h.type) ?? []), h]);
  return (
    <>
      <Button variant="outline" size="sm" className="w-9 justify-start text-muted-foreground sm:w-56" onClick={() => setOpen(true)} aria-label="Search everything">
        <Search /> <span className="hidden sm:inline">Search…</span><kbd className="ml-auto hidden rounded border px-1 text-[10px] sm:inline">⌘K</kbd>
      </Button>
      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setQ(""); }}>
        <DialogContent className="top-[15%] translate-y-0 sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Search the workspace</DialogTitle>
            <DialogDescription>Projects, tasks, knowledge, methodologies, documents, updates and notes.</DialogDescription>
          </DialogHeader>
          <Input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type at least two characters…" aria-label="Search" />
          <div className="max-h-[50vh] overflow-y-auto" aria-live="polite">
            {debounced.trim().length < 2 ? null : results.isPending ? <p className="py-4 text-sm text-muted-foreground">Searching…</p>
              : (results.data ?? []).length === 0 ? <p className="py-4 text-sm text-muted-foreground">Nothing found for “{debounced}”.</p>
              : [...groups.entries()].map(([type, hits]) => (
                <div key={type} className="py-2">
                  <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">{TYPE_LABEL[type]}</p>
                  <ul>
                    {hits.map((h) => (
                      <li key={`${h.type}-${h.id}`}>
                        <button className="w-full rounded-md px-2 py-1.5 text-left hover:bg-muted focus-visible:bg-muted" onClick={() => go(h)}>
                          <span className="block truncate text-sm font-medium">{h.title}</span>
                          <span className="block truncate text-xs text-muted-foreground">{[h.project_name, h.meta?.replace(/_/g, " "), h.snippet].filter(Boolean).join(" · ")}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
