"use client";
import { useState } from "react";
import { PageHeader, QueryView } from "@/components/common";
import { MilestoneList } from "@/components/milestones";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MILESTONE_STATUS_LABEL } from "@/lib/format";
import { useMilestones } from "@/lib/queries";

export default function MilestonesPage() {
  const q = useMilestones();
  const [status, setStatus] = useState("open");
  return (
    <>
      <PageHeader title="Milestones" description="Milestones across active projects, soonest first. Progress is weighted by task size; hover a bar to see how." />
      <div className="mb-4">
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-48" aria-label="Filter by status"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="open">Open (planned or in progress)</SelectItem>
            {Object.entries(MILESTONE_STATUS_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
            <SelectItem value="all">All</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <QueryView query={q}>
        {(ms) => <MilestoneList showProject milestones={ms.filter((m) =>
          status === "all" ? true : status === "open" ? m.status === "planned" || m.status === "in_progress" : m.status === status)} />}
      </QueryView>
      <p className="mt-3 text-xs text-muted-foreground">To add a milestone, open its project and use the Milestones tab.</p>
    </>
  );
}
