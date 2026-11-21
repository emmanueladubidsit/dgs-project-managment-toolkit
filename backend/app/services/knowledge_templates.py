"""Structured-field templates per knowledge category (single source of truth for API and UI).

Each field is (key, label, hint). Values are stored as text in KnowledgeItem.fields; unknown keys
are rejected so structure stays consistent and searchable."""

from app.models.knowledge import KnowledgeCategory as C

Field = tuple[str, str, str]

_RESEARCH: list[Field] = [
    ("research_question", "Research question", "What exactly are you trying to find out?"),
    ("objective", "Objective", "Why it matters and what decision it informs."),
    ("researcher", "Researcher / source", "Who researched it, or where it came from."),
    ("research_date", "Date", "When the research was done (YYYY-MM-DD)."),
    ("findings", "Findings", "What you found, stated factually."),
    ("options_investigated", "Options investigated", "One option per line."),
    ("comparisons", "Comparisons", "How the options compare (criteria, trade-offs)."),
    ("conclusions", "Conclusions", ""),
    ("recommendations", "Recommendations", ""),
    ("outstanding_questions", "Outstanding questions", "What is still unknown."),
    ("reuse_suitability", "Reuse suitability", "Where this applies, and where it does not."),
]
_TROUBLESHOOTING: list[Field] = [
    ("problem", "Problem", "One-sentence description of the problem."),
    ("symptoms", "Symptoms", "Error messages, behaviour observed."),
    ("environment", "Environment", "OS, versions, configuration."),
    ("root_cause", "Root cause", ""),
    ("investigation_steps", "Investigation steps", "What you checked, in order."),
    ("commands_used", "Commands and tools used", "Exact commands, one per line."),
    ("resolution_steps", "Resolution steps", "Steps someone can follow without help."),
    ("verification", "Verification", "How to confirm it is fixed."),
    ("prevention", "Prevention", "How to stop it happening again."),
    ("related_code_changes", "Related code changes", "Commits, branches or files."),
    ("related_session", "Related Claude session", "Session id or summary, if any."),
]
_DECISION: list[Field] = [
    ("context", "Context", "The situation and forces at play."),
    ("options_considered", "Options considered", "One option per line."),
    ("decision", "Decision", "What was decided."),
    ("rationale", "Rationale", "Why this option."),
    ("consequences", "Consequences", "Trade-offs and follow-on work."),
    ("decision_status", "Status", "Proposed, accepted or superseded."),
    ("decided_on", "Decided on", "Date (YYYY-MM-DD)."),
]
_LESSON: list[Field] = [
    ("what_happened", "What happened", ""),
    ("went_well", "What went well", ""),
    ("to_change", "What to change", ""),
    ("recommendation", "Recommendation for next time", ""),
]
_GUIDE: list[Field] = [
    ("purpose", "Purpose", ""),
    ("prerequisites", "Prerequisites", ""),
    ("steps", "Steps", "Numbered steps someone can follow."),
    ("verification", "Verification", "How to confirm success."),
    ("rollback", "Rollback", "How to undo, if needed."),
]
_CHECKLIST: list[Field] = [("items", "Checklist items", "One item per line.")]

TEMPLATES: dict[C, list[Field]] = {
    C.RESEARCH: _RESEARCH,
    C.TROUBLESHOOTING: _TROUBLESHOOTING,
    C.DECISION: _DECISION,
    C.LESSON_LEARNED: _LESSON,
    C.RUNBOOK: _GUIDE,
    C.SETUP_GUIDE: _GUIDE,
    C.PLAYBOOK: _GUIDE,
    C.CHECKLIST: _CHECKLIST,
}

LABELS: dict[C, str] = {
    C.RESEARCH: "Research",
    C.TROUBLESHOOTING: "Troubleshooting guide",
    C.RUNBOOK: "Technical runbook",
    C.PLAYBOOK: "Playbook",
    C.TECHNICAL_STANDARD: "Technical standard",
    C.DESIGN_STANDARD: "Design standard",
    C.ARCHITECTURE_PATTERN: "Architecture pattern",
    C.DECISION: "Decision",
    C.LESSON_LEARNED: "Lesson learned",
    C.TEMPLATE: "Template",
    C.REUSABLE_COMPONENT: "Reusable component",
    C.SETUP_GUIDE: "Setup guide",
    C.CHECKLIST: "Checklist",
    C.PROJECT_DOCUMENTATION: "Project documentation",
}


def allowed_keys(category: C) -> set[str]:
    return {k for k, _, _ in TEMPLATES.get(category, [])}


def clean_fields(category: C, fields: dict) -> dict:
    """Keep only template keys with non-empty string values; reject unknown keys."""
    unknown = set(fields) - allowed_keys(category)
    if unknown:
        raise ValueError(
            f"Unknown field(s) for {LABELS[category].lower()}: {', '.join(sorted(unknown))}."
        )
    out = {}
    for k, v in fields.items():
        if v is None:
            continue
        if not isinstance(v, str):
            raise ValueError(f"Field “{k}” must be text.")
        if len(v) > 50_000:
            raise ValueError(f"Field “{k}” is too long.")
        if v.strip():
            out[k] = v.strip()
    return out
