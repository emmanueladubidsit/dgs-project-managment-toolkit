# ADR 0007 — An integrated AI assistant that needs no new paid service

- **Status:** Accepted · 21 November 2026

## Context

The goal is one tool that brings AI into the workspace — answering questions about projects,
drafting writing, turning notes into tasks — without adding a new subscription. The preferred
sources were a free personal ChatGPT account or an AI service the organisation already provides.

## Facts that shaped the decision

- A **free (or Plus) ChatGPT account has no API**. Apps cannot call it. The only way would be
  automating the chatgpt.com website, which breaks OpenAI's terms of use and fails whenever the
  page changes — so it is not done.
- Most no-cost options speak the **OpenAI chat-completions API**: local runtimes (Ollama, LM
  Studio), organisation gateways and Azure OpenAI, Google Gemini's OpenAI-compatible endpoint
  (free tier), Groq and OpenRouter (free tiers/models).

## Decision

1. **One provider interface, three modes** (`backend/app/services/ai/provider.py`):
   *Off* (default), *Connected service* (any OpenAI-compatible endpoint, with presets) and
   *Copy and paste* — the app builds the full grounded prompt, the user runs it in any chat they
   already have (free ChatGPT, Copilot, Gemini) and pastes the answer back. Every feature works in
   every mode, through the same parsing and review steps.
2. **Recommended free setup: a local model via Ollama** (private, offline, no account). For work
   data, the organisation's approved service is the alternative.
3. **Grounded prompts only** (`services/ai/context.py`, `features.py`): the model receives
   selected workspace data (project, milestones, open tasks, recent updates, linked knowledge), is
   instructed to use only that, to say “not stated in the workspace” rather than guess, never to
   invent facts, dates or commitments, and to write in British English. Responses list the records
   that were supplied as context.
4. **Drafts and suggestions, never direct changes.** Suggested tasks, subtasks, blockers and
   decisions go into the existing `suggestions` review queue (duplicate checks included); project
   briefs open in the normal form; research drafts are saved as “AI suggestion — awaiting review”.
5. **Secrets and logging:** the API key is read only from `backend/.env` (`AI_API_KEY`), never
   stored in the database or sent to the browser. `ai_interactions` records metadata (feature,
   model, sizes, duration, errors) — never prompts or answers.

## Consequences

- Zero new cost in every mode; quality depends on the chosen model (an 8B local model is fine for
  drafting and extraction; larger models give better answers).
- Copy-and-paste mode adds a manual step but works with any chat tool, including a free ChatGPT
  account.
- Data leaves the machine only when the user chooses a remote service; the settings page says so.
