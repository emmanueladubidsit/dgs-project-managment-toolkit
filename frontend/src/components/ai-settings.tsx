"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, PlugZap, ShieldAlert, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useAIStatus, type AIStatus } from "./ai";
import { Section } from "./common";
import { SelectField, TextField } from "./form-fields";

const MODES = [
  { value: "disabled", label: "Off — the workspace works fully without AI" },
  { value: "openai_compatible", label: "Connected AI service (local model or organisation API)" },
  { value: "manual", label: "Copy and paste with any AI chat (no setup)" },
];

export function AISettings() {
  const status = useAIStatus();
  return status.data ? <AISettingsForm key={JSON.stringify(status.data)} s={status.data} /> : null;
}

function AISettingsForm({ s }: { s: AIStatus }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    provider: s.provider, preset: s.preset || "ollama", base_url: s.base_url, model: s.model,
    temperature: String(s.temperature), timeout_seconds: String(s.timeout_seconds),
  });
  const preset = s.presets[form.preset];
  const models = useQuery({ queryKey: ["ai-models", s.base_url], queryFn: () => api<{ models: string[] }>("/ai/models"), enabled: s.provider === "openai_compatible" });
  const usage = useQuery({ queryKey: ["ai-usage"], queryFn: () => api<{ feature: string; model: string | null; ok: boolean; error: string | null; duration_ms: number; created_at: string }[]>("/ai/usage") });
  const save = useMutation({
    mutationFn: () => api<AIStatus>("/ai/settings", { method: "PUT", body: { ...form, temperature: Number(form.temperature), timeout_seconds: Number(form.timeout_seconds) } }),
    onSuccess: () => { qc.invalidateQueries(); toast.success("AI settings saved."); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const test = useMutation({
    mutationFn: () => api<{ reply: string; seconds: number; model: string }>("/ai/test", { method: "POST" }),
    onSuccess: (r) => { qc.invalidateQueries({ queryKey: ["ai-usage"] }); toast.success(`Connected to ${r.model} — answered in ${r.seconds}s.`); },
    onError: (e) => { qc.invalidateQueries({ queryKey: ["ai-usage"] }); toast.error(errorMessage(e)); },
  });
  const local = form.base_url.startsWith("http://localhost") || form.base_url.startsWith("http://127.0.0.1");
  const dirty = form.provider !== s.provider || form.base_url !== s.base_url || form.model !== s.model || form.preset !== s.preset
    || Number(form.temperature) !== s.temperature || Number(form.timeout_seconds) !== s.timeout_seconds;

  return (
    <Section title="AI assistant" className="md:col-span-2">
      <div className="space-y-4">
        <SelectField label="How should the assistant work?" value={form.provider} onChange={(v) => setForm({ ...form, provider: (v ?? "disabled") as AIStatus["provider"] })} options={MODES} />

        {form.provider === "manual" && (
          <p className="rounded-lg bg-muted/60 px-3 py-2 text-sm">Each AI feature shows a prompt to copy into the chat you already use (for example ChatGPT, Copilot or Gemini), then you paste the answer back. No API, key or cost — but it is one extra step each time, and the prompt contains workspace data, so only use a chat service you are allowed to share it with.</p>
        )}

        {form.provider === "openai_compatible" && (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              <SelectField label="Service" value={form.preset} className="sm:col-span-2"
                onChange={(v) => { const p = s.presets[v ?? "custom"]; setForm({ ...form, preset: v ?? "custom", base_url: p?.base_url || form.base_url, model: p?.model || form.model }); }}
                options={Object.entries(s.presets).map(([value, p]) => ({ value, label: p.label }))} />
              <TextField label="Service address (OpenAI-compatible)" value={form.base_url} onChange={(v) => setForm({ ...form, base_url: v })} placeholder="https://…/v1" />
              <div className="space-y-1.5">
                <TextField label="Model" value={form.model} onChange={(v) => setForm({ ...form, model: v })} placeholder="e.g. llama3.1:8b" />
                {(models.data?.models.length ?? 0) > 0 && (
                  <div className="flex flex-wrap gap-1">{models.data!.models.slice(0, 12).map((m) => (
                    <Button key={m} size="xs" variant={m === form.model ? "default" : "outline"} onClick={() => setForm({ ...form, model: m })}>{m}</Button>
                  ))}</div>
                )}
              </div>
              <TextField label="Creativity (0–1.5)" type="number" min={0} max={1.5} step="0.1" value={form.temperature} onChange={(v) => setForm({ ...form, temperature: v })} hint="Lower is more factual. 0.3 is a good default." />
              <TextField label="Timeout (seconds)" type="number" min={5} max={900} value={form.timeout_seconds} onChange={(v) => setForm({ ...form, timeout_seconds: v })} hint="Local models on first use can be slow." />
            </div>
            <div className="rounded-lg border px-3 py-2 text-sm">
              {local ? (
                <p className="flex items-start gap-2"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />Runs on this computer: your data never leaves it and there is no cost.</p>
              ) : (
                <p className="flex items-start gap-2"><ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />Workspace data in each request is sent to this service. Use your organisation&apos;s approved service for work data; free tiers of public services may use your data for training.</p>
              )}
              {preset?.needs_key && (
                <p className={`mt-1 ${s.api_key_set ? "text-success" : "text-muted-foreground"}`}>
                  {s.api_key_set ? <><CheckCircle2 className="mr-1 inline size-4" />An API key is set.</> : <>This service needs an API key. Add <code className="rounded bg-muted px-1">AI_API_KEY=…</code> to <code className="rounded bg-muted px-1">backend/.env</code> and restart the API. Keys are never stored in the database or shown in the browser.</>}
                </p>
              )}
              {form.preset === "ollama" && (
                <p className="mt-1 text-muted-foreground">Ollama setup: install it from ollama.com, then run <code className="rounded bg-muted px-1">ollama pull {form.model || "llama3.1:8b"}</code>. It is free and runs offline.</p>
              )}
            </div>
          </>
        )}

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}>Save</Button>
          {s.provider === "openai_compatible" && !dirty && <Button variant="outline" onClick={() => test.mutate()} disabled={test.isPending}><PlugZap /> {test.isPending ? "Testing…" : "Test connection"}</Button>}
        </div>

        {(usage.data ?? []).length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer text-muted-foreground">Recent AI requests (no content is stored, only these details)</summary>
            <ul className="mt-2 space-y-1 text-xs">
              {usage.data!.slice(0, 15).map((u, i) => (
                <li key={i} className={u.ok ? "" : "text-destructive"}>{formatDateTime(u.created_at)} · {u.feature} · {u.model ?? "manual"} · {u.ok ? `${(u.duration_ms / 1000).toFixed(1)}s` : u.error}</li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </Section>
  );
}
