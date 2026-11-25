"use client";
// Administration: the "Keep to DGS" browser extension (ADR 0011).
import { Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { useClaudeSettings, useClaudeSetup, useSaveClaudeSettings } from "@/lib/queries-library";
import { Section } from "./common";

const copy = (t: string, what: string) =>
  navigator.clipboard.writeText(t).then(() => toast.success(what), () => toast.error("Copy blocked — select the text and copy it."));

export function BrowserExtensionPanel() {
  const setup = useClaudeSetup();
  const settings = useClaudeSettings();
  const save = useSaveClaudeSettings();
  const s = setup.data;
  return (
    <Section title="Browser extension: keep AI answers" className="md:col-span-2">
      <div className="space-y-3 text-sm">
        <p>
          Use ChatGPT, Claude, Gemini or Copilot in your browser as usual, signed in with your own account. The
          <strong> Keep to DGS</strong> extension adds a <strong>Keep</strong> tick box to each answer and <strong>Add to file</strong> to
          each code block. Only what you keep is stored here, as a note in the project&apos;s Library or as a progress update.
          Everything else stays in the AI tool&apos;s own history. No AI keys are used.
        </p>
        <p className="rounded-md bg-warning/10 px-3 py-2">Check that your organisation allows the AI tool and a browser extension for this work before installing it.</p>
        <ol className="list-decimal space-y-1 pl-5">
          <li>In Chrome or Edge, open <code className="text-xs">chrome://extensions</code>, turn on <strong>Developer mode</strong> and choose <strong>Load unpacked</strong>.</li>
          <li>Select the folder {s ? <code className="text-xs break-all">{s.extension_dir}</code> : "extension/ in this repository"}.</li>
          <li>Open the extension&apos;s settings (its toolbar icon), paste the token below, then <strong>Save and test</strong>.</li>
        </ol>
        {s && (
          <div className="flex gap-2">
            <code className="block flex-1 overflow-x-auto rounded-md bg-muted p-2 text-xs whitespace-nowrap" aria-label="Workspace token">{"•".repeat(16)}</code>
            <Button size="sm" variant="outline" onClick={() => copy(s.token, "Token copied. Keep it to yourself.")}><Copy /> Copy token</Button>
          </div>
        )}
        <label className="flex items-start gap-2">
          <Checkbox checked={!!settings.data?.allow_file_writes} disabled={!settings.data}
            onCheckedChange={(c) => save.mutate({ allow_file_writes: !!c })} className="mt-0.5" aria-label="Allow the browser extension to write files" />
          <span>
            <strong>Allow the browser extension to write files</strong> (off by default). <strong>Add to file</strong> always shows the new
            file, or the before/after, and writes only when you press Write. Writes stay inside the project&apos;s connected folder.
            Secret files (.env, keys), <code className="text-xs">.git</code> and dependency folders are never written, and a file changed since the preview is
            not overwritten.
          </span>
        </label>
      </div>
    </Section>
  );
}
