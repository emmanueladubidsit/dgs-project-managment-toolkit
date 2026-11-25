"""Project tracker files: `docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md`.

Claude Code (or a person) keeps one tracker per project. It records work done per working day,
milestone criteria with an explicit status, and the proposed plan for the coming weeks. This
module only *reads* the newest tracker and turns it into structured items; nothing is stored or
changed here (see `tracker_import` for the review queue). See ADR 0010.

Rules:
- Working days are Monday to Friday. Anything dated Saturday or Sunday counts on the following
  Monday (`working_day`).
- Status words are explicit: Verified/Done → completed, In progress → in_progress,
  Not started → todo, Blocked → blocked. Nothing is inferred from prose.
- Parsing fails soft: sections it does not recognise are ignored and reported as warnings.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from app.services import files

TRACKER_DIR = "docs/project-management"
TRACKER_RE = re.compile(r"^PROGRESS-AND-PLAN-(\d{4})-(\d{2})-(\d{2})\.md$", re.IGNORECASE)
MAX_BYTES = 512 * 1024

WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}
DAY_RE = re.compile(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\.?\s+(\d{1,2})\b", re.IGNORECASE)
NUM_MONTH_RE = re.compile(
    r"\b(\d{1,2})\b[^()\d]{0,25}?\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
MILESTONE_CODE_RE = re.compile(r",\s*(M\d{1,3})\s*[:\-–]\s*(.+)$")
CRITERIA_RE = re.compile(
    r"^\s*\*\*\s*(M\d{1,3})\s+success criteria\s*(?:\(([^)]*)\))?\s*:?\s*\*\*\s*:?\s*(.*)$",
    re.IGNORECASE,
)
MILESTONE_BLOCK_RE = re.compile(r"^\s*\*\*(.*\bmilestone\b.*?)\*\*\s*$", re.IGNORECASE)
STATUS_BULLET_RE = re.compile(
    r"^\s*[-*+]\s+(.+?)\s*:\s*\*\*\s*(verified|done|complete[d]?|in progress|not started|"
    r"blocked)\s*\*\*\s*(.*)$",
    re.IGNORECASE,
)
STATUS_MAP = {
    "verified": "completed",
    "done": "completed",
    "complete": "completed",
    "completed": "completed",
    "in progress": "in_progress",
    "not started": "todo",
    "blocked": "blocked",
}
CARRIED_RE = re.compile(r"\*\*\s*carried from ([^*:]+?)\s*:?\s*\*\*\s*:?\s*", re.IGNORECASE)
SKIP_ROW_RE = re.compile(
    r"(?i)^\W*(no record|none|nothing (recorded|done)|holiday|no planned work)\b"
)
NUMBERED_RE = re.compile(r"(?:^|\s)(\d{1,2})[.)]\s+")
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d{1,5}\b")


# ---------------------------------------------------------------- data
@dataclass
class TrackerItem:
    key: str
    kind: str  # done | status | plan
    title: str
    status: str  # task status: completed | in_progress | todo | blocked
    item_date: date | None  # working day (weekends already moved to Monday)
    original_date: date | None = None  # as written, when it differs (e.g. Saturday)
    section: str = ""
    milestone_key: str | None = None
    acceptance_criteria: str | None = None
    evidence: str = ""
    task_ids: list[str] = field(default_factory=list)


@dataclass
class TrackerMilestone:
    key: str
    title: str
    code: str | None
    due_date: date | None
    status: str  # milestone status: planned | in_progress | achieved
    description: str | None = None
    section: str = ""


@dataclass
class DayLog:
    key: str
    item_date: date
    text: str
    original_dates: list[date] = field(default_factory=list)
    section: str = ""


@dataclass
class Tracker:
    file_date: date
    items: list[TrackerItem] = field(default_factory=list)
    milestones: list[TrackerMilestone] = field(default_factory=list)
    days: list[DayLog] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sections_recognised: int = 0  # daily tables and milestone blocks, even when still empty


# ---------------------------------------------------------------- helpers
def working_day(d: date) -> date:
    """Saturday and Sunday count on the following Monday."""
    wd = d.weekday()
    return d + timedelta(days=7 - wd) if wd >= 5 else d


def _key(*parts: object) -> str:
    raw = "|".join(_norm(str(p)) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _plain(text: str) -> str:
    """Strip Markdown emphasis/code marks and tidy spacing."""
    t = re.sub(r"\*\*|__|`", "", text)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    return re.sub(r"\s+", " ", t).strip(" .;")


def _resolve(day: int, weekday: int | None, anchor: date) -> date | None:
    """The date with this day-of-month nearest to the anchor (matching the weekday if given)."""
    best: date | None = None
    for offset in (-1, 0, 1):
        y, m = anchor.year, anchor.month + offset
        if m == 0:
            y, m = y - 1, 12
        elif m == 13:
            y, m = y + 1, 1
        try:
            cand = date(y, m, day)
        except ValueError:
            continue
        if weekday is not None and cand.weekday() != weekday:
            continue
        if best is None or abs((cand - anchor).days) < abs((best - anchor).days):
            best = cand
    return best


def _dates_in(cell: str, anchor: date) -> list[date]:
    out = []
    for wd, num in DAY_RE.findall(cell):
        d = _resolve(int(num), WEEKDAYS[wd[:3].lower()], anchor)
        if d:
            out.append(d)
    return out


def _heading_anchor(text: str, fallback: date) -> date | None:
    """Start of a range such as '(Mon 16 to Fri 20 Nov)' or '(30 Nov to 4 Dec)'."""
    paren = re.search(r"\(([^)]*)\)", text)
    if not paren:
        return None
    m = NUM_MONTH_RE.search(paren.group(1))
    if not m:
        return None
    day, month = int(m.group(1)), MONTHS[m.group(2)[:3].lower()]
    best = None
    for y in (fallback.year - 1, fallback.year, fallback.year + 1):
        try:
            cand = date(y, month, day)
        except ValueError:
            continue
        if best is None or abs((cand - fallback).days) < abs((best - fallback).days):
            best = cand
    return best


def split_items(text: str) -> list[str]:
    """Split a table cell into items: a numbered list ('1. … 2. …') or sentences.
    Full stops inside brackets never split."""
    text = text.strip()
    if not text:
        return []
    if len(NUMBERED_RE.findall(text)) >= 2:
        parts = [p for p in NUMBERED_RE.split(text)]
        # re.split with a group returns [pre, n, item, n, item...]
        items = [parts[i] for i in range(2, len(parts), 2)]
        if parts[0].strip():
            items.insert(0, parts[0])
        return [_cap(s) for s in (_plain(i) for i in items) if s]
    out, buf, depth = [], [], 0
    for i, ch in enumerate(text):
        buf.append(ch)
        if ch in "([":
            depth += 1
        elif ch in ")]" and depth:
            depth -= 1
        elif ch in ".!?" and depth == 0:
            nxt = text[i + 1 : i + 3]
            if nxt[:1] in ("", " ") and (len(nxt) < 2 or not nxt[1].islower()):
                out.append("".join(buf))
                buf = []
    if "".join(buf).strip():
        out.append("".join(buf))
    return [_cap(s) for s in (_plain(x) for x in out) if len(s) > 2]


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _cells(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*", line))


def _section_title(heading: str) -> str:
    t = re.sub(r"^\d+(\.\d+)*\.?\s*", "", heading)
    t = re.sub(r"\s*\([^)]*\)", "", t)
    t = MILESTONE_CODE_RE.sub("", t)
    return _plain(t)


# ---------------------------------------------------------------- finding the file
def tracker_date(name: str) -> date | None:
    m = TRACKER_RE.match(name)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def find_tracker(root: str) -> tuple[str, date] | None:
    """The newest tracker (by the date in its name) in docs/project-management/."""
    folder = Path(root) / TRACKER_DIR
    if not folder.is_dir() or folder.is_symlink():
        return None
    found = [(d, p.name) for p in folder.iterdir() if p.is_file() and (d := tracker_date(p.name))]
    if not found:
        return None
    d, name = max(found)
    return f"{TRACKER_DIR}/{name}", d


def read_tracker(root: str) -> tuple[str, date, str] | None:
    hit = find_tracker(root)
    if not hit:
        return None
    rel, d = hit
    path = files.safe_file(root, rel)
    if path.stat().st_size > MAX_BYTES:
        raise files.PathError(f"{rel} is larger than 512 KB.")
    return rel, d, files.read_text(path)


# ---------------------------------------------------------------- parsing
def parse_tracker(text: str, file_date: date) -> Tracker:
    tr = Tracker(file_date=file_date)
    lines = text.splitlines()
    section, section_anchor = "", file_date
    section_ms: dict[str, str] = {}  # section → milestone key (plans and criteria)
    pending_section_items: dict[str, list[TrackerItem]] = {}
    block_ms: TrackerMilestone | None = None
    block_statuses: list[str] = []
    ms_by_code: dict[str, TrackerMilestone] = {}

    def close_block():
        nonlocal block_ms, block_statuses
        if block_ms and block_statuses:
            if all(s == "completed" for s in block_statuses):
                block_ms.status = "achieved"
            elif any(s in ("completed", "in_progress") for s in block_statuses):
                block_ms.status = "in_progress"
        block_ms, block_statuses = None, []

    def add_milestone(title, code, due, status, description=None) -> TrackerMilestone:
        if code and code in ms_by_code:
            ms = ms_by_code[code]
            ms.due_date = ms.due_date or due
            if description:
                ms.description = description
            return ms
        ms = TrackerMilestone(
            key=_key("milestone", code or title),
            title=title[:200],
            code=code,
            due_date=due,
            status=status,
            description=description,
            section=section,
        )
        tr.milestones.append(ms)
        if code:
            ms_by_code[code] = ms
        return ms

    i = 0
    while i < len(lines):
        line = lines[i]
        h = HEADING_RE.match(line)
        if h:
            close_block()
            section = _plain(h.group(2))
            section_anchor = _heading_anchor(h.group(2), file_date) or file_date
            mc = MILESTONE_CODE_RE.search(h.group(2))
            if mc:
                code, title = mc.group(1).upper(), _plain(mc.group(2))
                ms = add_milestone(f"{code}: {title}", code, None, "planned")
                section_ms[section] = ms.key
            i += 1
            continue

        crit = CRITERIA_RE.match(line)
        if crit:
            close_block()
            code = crit.group(1).upper()
            due_dates = _dates_in(crit.group(2) or "", section_anchor)
            criteria = [_plain(c) for c in re.split(r";", crit.group(3)) if _plain(c)]
            title = f"{code}: {_section_title(section)}" if section else code
            ms = add_milestone(
                title,
                code,
                working_day(due_dates[0]) if due_dates else None,
                "planned",
                "Success criteria:\n" + "\n".join(f"- {c}" for c in criteria) if criteria else None,
            )
            section_ms[section] = ms.key
            i += 1
            continue

        mb = MILESTONE_BLOCK_RE.match(line)
        if mb:
            close_block()
            label = _plain(mb.group(1)).rstrip(":")
            quoted = re.search(r"[\"“]([^\"”]+)[\"”]", label)
            base = re.split(r"\s*\(", label)[0].strip()
            title = f"{base}: {quoted.group(1)}" if quoted else base
            block_ms = add_milestone(title[:1].upper() + title[1:], None, None, "planned")
            section_ms.setdefault(section, block_ms.key)
            i += 1
            continue

        sb = STATUS_BULLET_RE.match(line)
        if sb and block_ms:
            name = _plain(sb.group(1))
            status = STATUS_MAP[sb.group(2).lower()]
            block_statuses.append(status)
            tr.items.append(
                TrackerItem(
                    key=_key("status", block_ms.key, name),
                    kind="status",
                    title=name[:300],
                    status=status,
                    item_date=None,
                    section=section,
                    milestone_key=block_ms.key,
                    evidence=_plain(line.strip(" -*")),
                    task_ids=ID_RE.findall(line),
                )
            )
            i += 1
            continue
        if block_ms and line.strip() and not line.lstrip().startswith(("-", "*", "+")):
            close_block()

        # Tables: header row followed by a separator row.
        if line.lstrip().startswith("|") and i + 1 < len(lines) and _is_separator(lines[i + 1]):
            header = [_plain(c).lower() for c in _cells(line)]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(_cells(lines[j]))
                j += 1
            _table(tr, header, rows, section, section_anchor, pending_section_items)
            i = j
            continue
        i += 1
    close_block()

    # Done and plan items belong to their section's milestone (heading or criteria line).
    for sec, items in pending_section_items.items():
        for it in items:
            it.milestone_key = it.milestone_key or section_ms.get(sec)
    # A milestone is due on the last working day of its work or plan. Weekend work carried to
    # Monday does not extend it past its own week.
    for ms in tr.milestones:
        if ms.due_date is None:
            dates = [
                it.item_date
                for it in tr.items
                if it.milestone_key == ms.key and it.item_date and not it.original_date
            ]
            ms.due_date = max(dates) if dates else None
    if not tr.sections_recognised and not tr.milestones:
        tr.warnings.append(
            "No work-done tables, milestone statuses or plan tables were recognised."
        )
    return tr


def _col(header: list[str], *names: str) -> int | None:
    for n in names:
        for idx, h in enumerate(header):
            if h == n or h.startswith(n):
                return idx
    return None


def _table(tr, header, rows, section, anchor, pending):
    day_c = _col(header, "day", "when", "date")
    done_c = _col(header, "what was done", "done", "work done")
    task_c = _col(header, "tasks", "task")
    when_c = _col(header, "done when", "acceptance")
    ev_c = _col(header, "evidence")
    if day_c is None or (done_c is None and task_c is None):
        return  # not a daily table (e.g. feature comparison)
    if done_c is not None and header[done_c] == "done when":
        done_c = None
    tr.sections_recognised += 1
    for cells in rows:
        if len(cells) <= max(c for c in (day_c, done_c, task_c) if c is not None):
            continue
        day_cell = cells[day_c]
        dates = _dates_in(day_cell, anchor)
        if not dates:
            if day_cell.strip():
                tr.warnings.append(f"{section}: could not read the date “{_plain(day_cell)}”.")
            continue
        written = dates[0]
        when = working_day(written)
        if done_c is not None:
            body = cells[done_c]
            if SKIP_ROW_RE.match(_plain(body)) or not _plain(body):
                continue
            evidence = _plain(cells[ev_c]) if ev_c is not None and ev_c < len(cells) else ""
            carried = None
            cm = CARRIED_RE.search(body)
            if cm:
                cd = _dates_in(cm.group(1), when)
                carried = cd[0] if cd else None
            texts = []
            for part in split_items(CARRIED_RE.sub("", body)):
                texts.append(part)
            originals = sorted({d for d in [written, carried] if d and d != when})
            tr.days.append(
                DayLog(
                    key=_key("day", when),
                    item_date=when,
                    text=_plain(body),
                    original_dates=originals,
                    section=section,
                )
            )
            for n, t in enumerate(texts):
                orig = carried if (carried and n == 0) else (written if written != when else None)
                it = TrackerItem(
                    key=_key("done", when, t),
                    kind="done",
                    title=t[:300],
                    status="completed",
                    item_date=when,
                    original_date=orig,
                    section=section,
                    evidence=f"{_plain(day_cell)}: {t}"
                    + (f" (evidence: {evidence})" if evidence else ""),
                    task_ids=ID_RE.findall(t),
                )
                tr.items.append(it)
                pending.setdefault(section, []).append(it)
        else:
            body = cells[task_c]
            if SKIP_ROW_RE.match(_plain(body)) or not _plain(body):
                continue
            criteria = _plain(cells[when_c]) if when_c is not None and when_c < len(cells) else None
            for t in split_items(body):
                it = TrackerItem(
                    key=_key("plan", when, t),
                    kind="plan",
                    title=t[:300],
                    status="todo",
                    item_date=when,
                    original_date=written if written != when else None,
                    section=section,
                    acceptance_criteria=criteria or None,
                    evidence=f"{_plain(day_cell)}: {t}",
                    task_ids=ID_RE.findall(t),
                )
                tr.items.append(it)
                pending.setdefault(section, []).append(it)
