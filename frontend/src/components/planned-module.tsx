"use client";
import { MessageSquarePlus } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "./common";
import { WorkLogDialog } from "./work-log-dialog";

/** Honest placeholder for a module scheduled in a later phase. No fake data or controls. */
export function PlannedModule({ title, phase, purpose, features, interim }: {
  title: string; phase: string; purpose: string; features: string[]; interim?: ReactNode;
}) {
  return (
    <>
      <PageHeader title={title} description={purpose} />
      <div className="max-w-2xl rounded-xl border bg-card p-6">
        <p className="mb-1 text-xs font-medium tracking-wide text-primary uppercase">Planned for {phase}</p>
        <h2 className="mb-3 font-semibold">This module has not been built yet</h2>
        <p className="mb-2 text-sm text-muted-foreground">It is intentionally not mocked up. When implemented it will provide:</p>
        <ul className="mb-4 list-disc space-y-1 pl-5 text-sm">{features.map((f) => <li key={f}>{f}</li>)}</ul>
        {interim && <div className="rounded-lg bg-muted/60 p-3 text-sm">{interim}</div>}
      </div>
    </>
  );
}

export function RecordResearchInterim() {
  return (
    <>
      <p className="mb-2"><strong>In the meantime:</strong> record research findings and decisions as updates. They are stored, shown on each project’s “Decisions &amp; updates” tab and included in reports, ready to migrate into knowledge records.</p>
      <WorkLogDialog defaults={{ kind: "research" }} trigger={<Button size="sm" variant="outline"><MessageSquarePlus /> Record research now</Button>} />
    </>
  );
}
