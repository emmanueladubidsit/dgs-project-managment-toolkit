"use client";
import { PlannedModule } from "@/components/planned-module";

export default function DocumentsPage() {
  return <PlannedModule title="Documents & Artefacts" phase="Phase 7"
    purpose="Index and link project documents where they already live, without moving or copying them."
    features={["Register project directories with path validation and access safeguards",
      "Metadata, categorisation and linking for briefs, ADRs, diagrams, specifications and reports",
      "Never moves, deletes or modifies existing files without explicit approval"]}
    interim={<p>For now, record a project’s repository and documentation location on the project itself (Edit → more fields).</p>} />;
}
