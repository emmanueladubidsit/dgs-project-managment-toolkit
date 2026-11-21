# ADR 0006 — Local, optional transcription; deterministic writing tools; nothing faked

- **Status:** Accepted · 21 November 2026

## Context

Voice and writing must work without a paid service, keep recordings only when necessary, never
invent facts or commitments, and turn speech into suggestions that a person approves.

## Decision

- **Transcription sits behind `TranscriptionProvider`** (`services/transcription.py`). The
  default “auto” uses local **faster-whisper** when the optional `voice` extra is installed
  (`uv sync --extra voice`); otherwise transcription is reported unavailable and the user can type
  or paste. Audio never leaves the machine with the local provider. Cloud providers can be added
  as new implementations.
- **Retention:** `VOICE_RETENTION=delete` (default) deletes audio immediately after
  transcription; `keep` stores it under `backend/data/recordings/` (git-ignored) until the user
  deletes it. Failed transcriptions never keep the file.
- **Writing tools are deterministic** (`services/text_tools.py`): filler and repeated-word
  removal, spacing, capitalisation, conservative British spelling, and regrouping of the user's own
  sentences into structured notes, meeting notes, daily updates and task breakdowns.
- **Outputs that genuinely need a language model** (professional rewrite, summary, weekly update,
  requirements, email draft, brainstorming record) are listed but return `needs_ai` with an
  explanation. They are never approximated with templates that might read as real content.
- **Suggestions** are extracted by phrase rules into a `suggestions` table with the source
  sentence as evidence. Tasks are created only on approval; likely duplicates of existing tasks
  (normalised title, ≥ 80 % word overlap) are flagged and need explicit confirmation; re-running
  extraction never duplicates suggestions.

## Consequences

- Fully usable offline and free; quality of rule-based extraction is modest but transparent.
- The AI-dependent outputs slot in behind a future provider interface (Phase 8) with the same
  review workflow.
- `faster-whisper` 1.2 needs PyAV < 16 (newer PyAV removed an argument it passes); the extra pins
  `av>=14,<16`.
