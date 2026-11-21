"""Prompts and parsing for each AI feature. Every feature is grounded in workspace context and
produces drafts or suggestions that a person reviews — never direct changes."""

import json
import re

GROUNDING = (
    "You are the assistant inside a personal project and engineering workspace. Write in British "
    "English. Use ONLY the information in the CONTEXT and the user's text. If something is not "
    "stated, say “not stated in the workspace” instead of guessing. Never invent facts, figures, "
    "dates, names, decisions, commitments or project status. Be concise and practical."
)

WRITING = {
    "professional_rewrite": (
        "Professional rewrite",
        "Rewrite the user's text clearly and professionally. Keep every fact and meaning; add nothing.",
    ),
    "concise_summary": (
        "Concise summary",
        "Summarise the user's text in at most five sentences. Do not add information.",
    ),
    "weekly_update": (
        "Weekly update",
        "Turn the text (and the project context, if given) into a weekly update with headings: "
        "Achievements, In progress, Blockers and risks, Next week. Only include what is stated.",
    ),
    "requirements": (
        "Requirements",
        "Extract requirements from the text as Markdown: Functional requirements, Non-functional "
        "requirements, Assumptions, Open questions. Mark anything uncertain as an assumption.",
    ),
    "email_draft": (
        "Email draft",
        "Draft a reply email to the text below, using the project context where relevant. Do not "
        "promise dates, deliverables or decisions that are not in the context — leave [placeholders] "
        "instead. Start with a subject line.",
    ),
    "brainstorming_record": (
        "Brainstorming record",
        "Organise the text into a brainstorming record: Ideas (grouped), Questions raised, "
        "Possible next steps. Keep the user's ideas; do not judge or add new ones.",
    ),
}


def writing_prompt(
    output: str, text: str, context: str, instructions: str | None
) -> tuple[str, str]:
    label, task = WRITING[output]
    user = f"TASK: {task}\n"
    if instructions:
        user += f"EXTRA INSTRUCTIONS FROM THE USER: {instructions}\n"
    user += f"\nCONTEXT:\n{context or '(no project context)'}\n\nTEXT:\n{text}"
    return GROUNDING, user


def ask_prompt(question: str, context: str) -> tuple[str, str]:
    return GROUNDING + (
        " Answer the question from the context. When you rely on a specific item, "
        "name it. If the context does not contain the answer, say so plainly."
    ), f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"


SUGGEST_SCHEMA = (
    'Return ONLY a JSON array. Each element: {"kind": "task"|"blocker"|"decision"|"progress", '
    '"title": "short imperative title (tasks) or one-sentence statement", "evidence": "the exact '
    'sentence it came from", "priority": "critical"|"high"|"medium"|"low", "estimate_hours": number '
    'or null, "acceptance_criteria": "what done means, or empty"}. Only include items clearly '
    "supported by the text. Do not repeat tasks listed as EXISTING TASKS."
)


def suggest_prompt(text: str, context: str, existing: list[str]) -> tuple[str, str]:
    user = (
        f"TASK: Identify proposed actions (tasks), blockers, decisions and progress in the TEXT. "
        f"{SUGGEST_SCHEMA}\n\nEXISTING TASKS:\n"
        + "\n".join(f"- {t}" for t in existing[:80])
        + f"\n\nCONTEXT:\n{context}\n\nTEXT:\n{text}"
    )
    return GROUNDING, user


def breakdown_prompt(
    task_title: str, task_detail: str, context: str, existing: list[str]
) -> tuple[str, str]:
    user = (
        "TASK: Break the TASK below into 3–8 concrete subtasks someone can complete in a day or less. "
        'Return ONLY a JSON array of {"title": "...", "estimate_hours": number or null, '
        '"acceptance_criteria": "..."}. Do not repeat EXISTING SUBTASKS. Base it on the task and '
        "project context; do not invent requirements.\n\n"
        f"TASK: {task_title}\n{task_detail}\n\nEXISTING SUBTASKS:\n"
        + "\n".join(f"- {t}" for t in existing)
        + f"\n\nCONTEXT:\n{context}"
    )
    return GROUNDING, user


PROJECT_FIELDS = [
    "name",
    "description",
    "problem_statement",
    "objectives",
    "target_users",
    "business_context",
    "scope",
    "out_of_scope",
    "expected_outcomes",
    "risks_assumptions",
    "dependencies",
    "tech_stack",
]


def structure_project_prompt(idea: str) -> tuple[str, str]:
    user = (
        "TASK: Organise the IDEA into a project brief. Return ONLY a JSON object with these string "
        f'keys: {", ".join(PROJECT_FIELDS)}, plus "workstreams" (array of short names), '
        '"unknowns" (array of open questions) and "assumptions" (array). Use only what the idea '
        "says; put guesses under assumptions and gaps under unknowns. Use an empty string for "
        "anything not stated. Objectives: one per line.\n\nIDEA:\n" + idea
    )
    return GROUNDING, user


def research_prompt(question: str, notes: str, context: str) -> tuple[str, str]:
    user = (
        "TASK: Draft a research record from the NOTES (and relevant knowledge in the context). Return "
        'ONLY a JSON object with string keys: "title", "summary", "research_question", "objective", '
        '"findings", "options_investigated", "comparisons", "conclusions", "recommendations", '
        '"outstanding_questions", "limitations". Base findings only on the notes and context; say '
        "clearly where evidence is missing. Do not fabricate sources.\n\n"
        f"QUESTION: {question}\n\nNOTES:\n{notes or '(none)'}\n\nCONTEXT:\n{context}"
    )
    return GROUNDING, user


def report_summary_prompt(report: str) -> tuple[str, str]:
    user = (
        "TASK: Write a short executive summary (one paragraph, then up to three key points as "
        "bullets) of this REPORT for stakeholders. Use only what the report says; do not add "
        "achievements, figures or dates.\n\nREPORT:\n" + report[:14000]
    )
    return GROUNDING, user


def parse_json(text: str):
    """Extract the first JSON value from a model reply (tolerates prose and code fences)."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    pairs = sorted(
        (("[", "]"), ("{", "}")), key=lambda p: (cleaned.find(p[0]) == -1, cleaned.find(p[0]))
    )
    for opener, closer in pairs:
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(
        "The AI answer was not in the expected format. Try again, or use a larger model."
    )
