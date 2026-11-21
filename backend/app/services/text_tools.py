"""Deterministic writing tools (no AI): cleaning, restructuring and rule-based extraction.

These never add facts: they only remove filler, fix spacing/capitalisation, regroup the user's
own sentences, and flag sentences that look like actions, blockers or decisions."""

import re

FILLERS = [
    r"\bum+\b",
    r"\buh+\b",
    r"\ber+m*\b",
    r"\bah+\b",
    r"\bhmm+\b",
    r"\byou know,?\s*",
    r"\bi mean,?\s*",
    r"\bkind of\b\s*",
    r"\bsort of\b\s*",
    r"\bbasically,?\s*",
    r"\bactually,?\s*",
    r"\bliterally,?\s*",
    r"(?<=[\s,])like,\s*",  # only the comma-delimited filler "like,"
]
_FILLER_RE = re.compile("|".join(FILLERS), re.IGNORECASE)
_REPEAT_RE = re.compile(r"\b(\w+)(\s+\1\b)+", re.IGNORECASE)  # "the the" -> "the"

# Conservative US→UK spelling fixes for common workplace words only.
UK = {
    "color": "colour",
    "colors": "colours",
    "behavior": "behaviour",
    "organize": "organise",
    "organized": "organised",
    "organization": "organisation",
    "prioritize": "prioritise",
    "prioritized": "prioritised",
    "analyze": "analyse",
    "analyzed": "analysed",
    "center": "centre",
    "favorite": "favourite",
    "summarize": "summarise",
    "optimize": "optimise",
    "optimized": "optimised",
    "finalize": "finalise",
    "finalized": "finalised",
    "standardize": "standardise",
    "standardized": "standardised",
    "realize": "realise",
    "realized": "realised",
    "catalog": "catalogue",
    "license": "licence",
}
_UK_RE = re.compile(r"\b(" + "|".join(UK) + r")\b", re.IGNORECASE)

ACTION_PATTERNS = re.compile(
    r"^(?:(?:i|we)\s+(?:need|have|must|should|will|'ll|am going|are going)\s+to\s+|"
    r"(?:i|we)'ll\s+|(?:need|have)\s+to\s+|(?:todo|to do|action|next step|next)\s*[:\-]\s*|"
    r"let'?s\s+|remember\s+to\s+|don'?t forget\s+to\s+|make sure\s+(?:to|we|i)\s+)",
    re.IGNORECASE,
)
BLOCKER_PATTERNS = re.compile(
    r"\b(blocked|blocker|stuck|waiting (?:on|for)|can(?:no|')t proceed|unable to|depends on)\b",
    re.IGNORECASE,
)
DECISION_PATTERNS = re.compile(
    r"\b(we decided|i decided|decision(?: is| was)?:?|we(?:'ve| have) agreed|agreed to|"
    r"we(?:'re| are) going with|we will use|chose to|settled on)\b",
    re.IGNORECASE,
)
PROGRESS_PATTERNS = re.compile(
    r"\b(i|we)\s+(finished|completed|fixed|built|shipped|implemented|wrote|deployed|"
    r"merged|resolved|set up|tested)\b",
    re.IGNORECASE,
)


def _fix_spacing(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,;:])(?=\S)", r"\1 ", text)
    text = re.sub(r",\s*,+", ",", text)
    text = re.sub(r"(^|[.!?]\s+),\s*", r"\1", text)
    return text.strip()


def _uk(m: re.Match) -> str:
    word = m.group(0)
    repl = UK[word.lower()]
    return repl.capitalize() if word[0].isupper() else repl


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    # Speech transcripts are often lower-case, so split on terminal punctuation regardless of
    # case, but not after common abbreviations.
    parts = re.split(r"(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\betc\.)(?<!\bvs\.)(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _sentence_case(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    s = s[0].upper() + s[1:]
    s = re.sub(r"\bi\b", "I", s)
    if s[-1] not in ".!?":
        s += "."
    return s


def clean(text: str) -> str:
    """Remove filler words and repeated words; fix spacing, capitalisation and UK spelling."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    out = []
    for para in paragraphs:
        p = _FILLER_RE.sub(" ", para)
        p = _REPEAT_RE.sub(r"\1", p)
        p = _UK_RE.sub(_uk, p)
        p = _fix_spacing(p)
        sentences = [_sentence_case(s) for s in split_sentences(p)]
        if sentences:
            out.append(" ".join(sentences))
    return "\n\n".join(out)


def bullets(text: str) -> str:
    return "\n".join(f"- {s}" for s in split_sentences(clean(text)))


def classify(sentence: str) -> str:
    if DECISION_PATTERNS.search(sentence):
        return "decision"
    if BLOCKER_PATTERNS.search(sentence):
        return "blocker"
    if ACTION_PATTERNS.search(sentence.strip()):
        return "action"
    if PROGRESS_PATTERNS.search(sentence):
        return "progress"
    return "note"


def task_title(sentence: str) -> str:
    """Turn 'We need to update the API docs.' into 'Update the API docs'."""
    s = ACTION_PATTERNS.sub("", sentence.strip()).strip()
    s = s.rstrip(".!? ")
    return (s[0].upper() + s[1:])[:300] if s else sentence.strip()[:300]


def structured(text: str) -> str:
    groups: dict[str, list[str]] = {
        "progress": [],
        "decision": [],
        "blocker": [],
        "action": [],
        "note": [],
    }
    for s in split_sentences(clean(text)):
        groups[classify(s)].append(s)
    titles = {
        "progress": "Progress",
        "decision": "Decisions",
        "blocker": "Blockers",
        "action": "Actions",
        "note": "Notes",
    }
    parts = []
    for key, title in titles.items():
        if groups[key]:
            items = [f"- {task_title(s) if key == 'action' else s}" for s in groups[key]]
            parts.append(f"## {title}\n\n" + "\n".join(items))
    return "\n\n".join(parts) or "_Nothing to structure._"


def meeting_notes(text: str) -> str:
    body = structured(text)
    return "# Meeting notes\n\n**Date:** \n**Attendees:** \n\n" + body.replace(
        "## Progress", "## Updates"
    ).replace("## Notes", "## Discussion")


def research_notes(text: str) -> str:
    sentences = split_sentences(clean(text))
    findings = "\n".join(f"- {s}" for s in sentences) or "-"
    return (
        "# Research notes\n\n**Question:** \n\n## Findings\n\n"
        + findings
        + "\n\n## Sources\n\n- \n\n## Outstanding questions\n\n- "
    )


def daily_update(text: str) -> str:
    return structured(text).replace("## Actions", "## Next steps")


def task_breakdown(text: str) -> str:
    actions = [task_title(s) for s in split_sentences(clean(text)) if classify(s) == "action"]
    if not actions:
        return (
            "_No action items were found. Phrases like “we need to…”, “I’ll…” and "
            "“next step:” are detected._"
        )
    return "\n".join(f"- [ ] {a}" for a in actions)


DETERMINISTIC = {
    "clean_transcript": ("Clean transcript", clean),
    "bullet_points": ("Bullet points", bullets),
    "structured_notes": ("Structured notes", structured),
    "daily_update": ("Daily update", daily_update),
    "meeting_notes": ("Meeting notes", meeting_notes),
    "research_notes": ("Research notes", research_notes),
    "task_breakdown": ("Task breakdown", task_breakdown),
}
NEEDS_AI = {
    "professional_rewrite": "Professional rewrite",
    "concise_summary": "Concise summary",
    "weekly_update": "Weekly update",
    "requirements": "Requirements",
    "email_draft": "Email draft",
    "brainstorming_record": "Brainstorming record",
}


def extract(text: str) -> list[dict]:
    """Rule-based suggestions: one per action, blocker, decision or progress sentence."""
    out = []
    for s in split_sentences(clean(text)):
        kind = classify(s)
        if kind == "action":
            out.append({"kind": "task", "title": task_title(s), "evidence": s})
        elif kind in ("blocker", "decision", "progress"):
            out.append({"kind": kind, "title": s.rstrip("."), "evidence": s})
    return out


def normalise_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def similar(a: str, b: str) -> bool:
    """Duplicate check: identical when normalised, or ≥ 80% word overlap."""
    na, nb = normalise_title(a), normalise_title(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    wa, wb = set(na.split()), set(nb.split())
    return len(wa & wb) / max(len(wa | wb), 1) >= 0.8
