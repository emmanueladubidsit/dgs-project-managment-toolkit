"use client";
import { PlannedModule } from "@/components/planned-module";

export default function MethodologiesPage() {
  return <PlannedModule title="Methodologies & Playbooks" phase="Phase 7"
    purpose="A global library of reusable methodologies, playbooks, templates and starter kits."
    features={["Methodologies with stages, activities, instructions and expected deliverables",
      "Deliverables classed as mandatory, recommended, optional or not applicable", "Adopt a methodology into a project, or reuse individual steps",
      "Provenance, version history and record of where each artefact has been reused"]} />;
}
