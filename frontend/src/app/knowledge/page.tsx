"use client";
import { PlannedModule, RecordResearchInterim } from "@/components/planned-module";

export default function KnowledgePage() {
  return <PlannedModule title="Knowledge & Research" phase="Phase 6" interim={<RecordResearchInterim />}
    purpose="Preserve research, troubleshooting guides, runbooks, decisions and lessons learned so they can be reused across projects."
    features={["Research records with questions, sources, findings, options, conclusions and limitations",
      "Troubleshooting guides you can follow later without Claude", "Clear verification status — unverified AI output is never shown as fact",
      "Association with multiple projects, categorisation and global search"]} />;
}
