"""Privacy filters applied to text entering the workspace from outside (Claude Code, git) and to
text leaving it (AI prompts, exports): masks named individuals and redacts likely secrets."""

import re

from sqlalchemy.orm import Session

from app.models.system import SystemSetting

KEY = "privacy"

SECRET_PATTERNS = [
    re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{16,}"),  # OpenAI / Anthropic style keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),  # GitHub tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),  # Slack tokens
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),  # Google API keys
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[^\s'\"]{6,}"),
]


def redact_secrets(text: str) -> str:
    for pat in SECRET_PATTERNS:
        text = pat.sub("[redacted]", text)
    return text


def name_rules(db: Session) -> list[dict]:
    row = db.get(SystemSetting, KEY)
    rules = (row.value or {}).get("names", []) if row else []
    return [r for r in rules if isinstance(r, dict) and str(r.get("name", "")).strip()]


def save_name_rules(db: Session, rules: list[dict]) -> list[dict]:
    clean = []
    for r in rules:
        name = str(r.get("name", "")).strip()
        if len(name) < 2:
            continue
        clean.append(
            {"name": name[:120], "replacement": str(r.get("replacement") or "a colleague")[:120]}
        )
    row = db.get(SystemSetting, KEY) or SystemSetting(key=KEY, value={})
    row.value = {**(row.value or {}), "names": clean}
    db.add(row)
    db.commit()
    return clean


def mask_names(text: str, rules: list[dict]) -> str:
    # Longest names first so "Jane Smith" is replaced before "Jane".
    for r in sorted(rules, key=lambda x: -len(x["name"])):
        text = re.sub(
            rf"(?i)\b{re.escape(r['name'])}\b(?:'s)?",
            lambda m, rep=r["replacement"]: (
                rep + ("'s" if m.group(0).lower().endswith("'s") else "")
            ),
            text,
        )
    return text


def clean(db: Session, text: str | None, limit: int | None = None) -> str | None:
    """Redact secrets and mask names; optionally truncate."""
    if text is None:
        return None
    out = mask_names(redact_secrets(text), name_rules(db))
    if limit and len(out) > limit:
        out = out[: limit - 1] + "…"
    return out
