"use client";
// AI plumbing shared by every feature: status, the manual (copy/paste) round trip, sources and
// downloads. Every AI result is a draft the user reviews — nothing is saved automatically.
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, Download, ExternalLink, Sparkles } from "lucide-react";
import Link from "next/link";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError, errorMessage } from "@/lib/api";

export interface AIStatus {
  provider: "disabled" | "openai_compatible" | "manual";
  preset: string;
  base_url: string;
  model: string;
  temperature: number;
  timeout_seconds: number;
  max_context_chars: number;
  api_key_set: boolean;
  is_local: boolean;
  ready: boolean;
  presets: Record<string, { label: string; base_url: string; model: string; needs_key: boolean }>;
  writing_outputs: { key: string; label: string }[];
}

export type Source = { type: string; id: string; title: string };

export const useAIStatus = () => useQuery({ queryKey: ["ai-status"], queryFn: () => api<AIStatus>("/ai/status") });

type Pending = { prompt: string; resolve: (answer: string) => void; reject: (e: Error) => void };
const Ctx = createContext<((prompt: string) => Promise<string>) | null>(null);

/** Hosts the copy/paste dialog used when the provider is "manual". */
export function AIManualProvider({ children }: { children: ReactNode }) {
  const [pending, setPending] = useState<Pending | null>(null);
  const [answer, setAnswer] = useState("");
  const ask = useCallback((prompt: string) => new Promise<string>((resolve, reject) => {
    setAnswer("");
    setPending({ prompt, resolve, reject });
  }), []);
  const close = () => { pending?.reject(new Error("cancelled")); setPending(null); };
  return (
    <Ctx.Provider value={ask}>
      {children}
      <Dialog open={!!pending} onOpenChange={(o) => !o && close()}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Run this in your AI chat</DialogTitle>
            <DialogDescription>
              Copy the prompt into any AI chat you already use (for example ChatGPT, Copilot or Gemini), then paste its full answer below.
              The prompt contains workspace data for this request — only use a chat service you are allowed to share it with.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">1. Copy the prompt</span>
              <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(pending?.prompt ?? "").then(() => toast.success("Prompt copied."), () => toast.error("Copy blocked — select the text and copy it."))}><Copy /> Copy prompt</Button>
            </div>
            <Textarea readOnly value={pending?.prompt ?? ""} rows={8} className="font-mono text-xs" aria-label="Prompt to copy" />
            <span className="block pt-2 text-sm font-medium">2. Paste the AI&apos;s answer</span>
            <Textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={8} aria-label="Paste the AI answer" placeholder="Paste the full answer here…" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={close}>Cancel</Button>
            <Button disabled={!answer.trim()} onClick={() => { pending?.resolve(answer); setPending(null); }}>Use this answer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Ctx.Provider>
  );
}

/** Call an AI endpoint; transparently handles manual mode. Returns null if the user cancels. */
export function useAICall() {
  const askManual = useContext(Ctx);
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const call = useCallback(async <T,>(path: string, body: Record<string, unknown>): Promise<T | null> => {
    if (busyRef.current) return null;
    busyRef.current = true;
    setBusy(true);
    try {
      let res = await api<T | { needs_manual: true; prompt: string }>(path, { method: "POST", body });
      if (res && typeof res === "object" && "needs_manual" in res) {
        if (!askManual) throw new Error("Manual mode is unavailable.");
        let answer: string;
        try { answer = await askManual(res.prompt); } catch { return null; }
        res = await api<T>(path, { method: "POST", body: { ...body, manual_response: answer } });
      }
      qc.invalidateQueries();
      return res as T;
    } catch (e) {
      const msg = e instanceof ApiError && e.code === "ai_unavailable"
        ? `${e.message}` : errorMessage(e);
      toast.error(msg);
      return null;
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }, [askManual, qc]);
  return { call, busy };
}

/** Shown wherever an AI feature lives but no provider is set up. */
export function AIOffNotice({ compact }: { compact?: boolean }) {
  return (
    <p className={compact ? "text-xs text-muted-foreground" : "rounded-lg bg-muted/60 px-3 py-2 text-sm text-muted-foreground"}>
      <Sparkles className="mr-1 inline size-3.5" aria-hidden />
      The AI assistant is off. <Link href="/admin" className="underline">Turn it on in Administration</Link> — it can use a free local model or your organisation&apos;s AI service.
    </p>
  );
}

export function AIBadge() {
  return <span className="inline-flex items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary"><Sparkles className="size-3" aria-hidden />AI draft — review before use</span>;
}

const SOURCE_HREF: Record<string, (id: string) => string | null> = {
  project: (id) => `/projects/${id}`, knowledge: (id) => `/knowledge/${id}`, milestone: () => "/milestones", task: () => null,
};

export function Sources({ sources }: { sources: Source[] }) {
  if (!sources.length) return <p className="text-xs text-muted-foreground">No workspace records were used.</p>;
  const unique = [...new Map(sources.map((s) => [`${s.type}-${s.id}`, s])).values()];
  return (
    <details className="text-xs">
      <summary className="cursor-pointer text-muted-foreground">Context used: {unique.length} workspace record(s)</summary>
      <ul className="mt-1 space-y-0.5">
        {unique.slice(0, 60).map((s) => {
          const href = SOURCE_HREF[s.type]?.(s.id);
          return <li key={`${s.type}-${s.id}`}><span className="text-muted-foreground">{s.type}: </span>{href ? <Link className="underline" href={href}>{s.title}</Link> : s.title}</li>;
        })}
      </ul>
    </details>
  );
}

// ---------------------------------------------------------------- downloads
export async function downloadPost(title: string, content: string, format: "docx" | "pdf" | "pptx", subtitle?: string) {
  const res = await fetch("/api/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title, content, format, subtitle }) });
  if (!res.ok) { toast.error("The export failed."); return; }
  const blob = await res.blob();
  const name = res.headers.get("content-disposition")?.match(/filename="([^"]+)"/)?.[1] ?? `export.${format}`;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function ExportMenu({ label = "Export", items }: { label?: string; items: { group?: string; label: string; href?: string; onSelect?: () => void }[] }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild><Button variant="outline"><Download /> {label}</Button></DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {items.map((it, i) => {
          const header = !!it.group && it.group !== items[i - 1]?.group;
          return (
            <div key={i}>
              {header && i > 0 && <DropdownMenuSeparator />}
              {header && <DropdownMenuLabel>{it.group}</DropdownMenuLabel>}
              {it.href
                ? <DropdownMenuItem asChild><a href={it.href} download><ExternalLink className="size-3.5 opacity-0" aria-hidden />{it.label}</a></DropdownMenuItem>
                : <DropdownMenuItem onSelect={it.onSelect}>{it.label}</DropdownMenuItem>}
            </div>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
