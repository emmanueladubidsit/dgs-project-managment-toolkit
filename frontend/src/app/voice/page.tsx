"use client";
import { PlannedModule } from "@/components/planned-module";

export default function VoicePage() {
  return <PlannedModule title="Voice & Writing" phase="Phase 9"
    purpose="Record, transcribe and turn speech into clean notes, updates and suggested tasks."
    features={["Record, pause, resume, play back and transcribe — local Whisper-based option first",
      "Clean transcripts, summaries, daily updates, meeting notes and email drafts in British English",
      "Spoken updates become suggested task changes that you review before anything is saved",
      "Configurable retention; recordings are not stored unnecessarily"]} />;
}
