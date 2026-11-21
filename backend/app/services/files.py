"""Read-only, validated file access for registered document roots.

Guarantees: paths are resolved (symlinks included) and must stay inside the registered root;
sensitive files are never listed or read; nothing is ever written, moved or deleted."""

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.models.documents import DocumentCategory as C

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".cache",
    ".idea",
    ".vscode",
    "target",
    ".pytest_cache",
    ".ruff_cache",
    "graphify-out",
    ".mypy_cache",
    ".turbo",
    "coverage",
}
SENSITIVE = re.compile(
    r"(^\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|\.kdbx$|^id_(rsa|dsa|ecdsa|ed25519)|"
    r"^\.netrc$|^\.npmrc$|^\.pypirc$|credential|secret|\.keystore$|\.jks$)",
    re.IGNORECASE,
)
TEXT_EXT = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".adoc",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".csv",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".html",
    ".css",
    ".sql",
    ".sh",
    ".mmd",
    ".puml",
    ".drawio",
    ".xml",
    ".ini",
    ".cfg",
}
MAX_PREVIEW = 512 * 1024
MAX_SCAN_FILES = 5000
MAX_DEPTH = 8
HOME = Path.home().resolve()
# Too broad to register as a whole (subfolders are fine):
EXACT_FORBIDDEN = {Path("/"), HOME, Path("/Users"), Path("/Volumes")}
# System areas — never registrable, including anything inside them:
TREE_FORBIDDEN = [
    Path(p)
    for p in (
        "/System",
        "/Library",
        "/usr",
        "/bin",
        "/sbin",
        "/etc",
        "/private",
        "/var",
        "/opt",
        "/Applications",
        "/dev",
    )
]


class PathError(ValueError):
    pass


def validate_root(raw: str) -> Path:
    if not raw or not raw.strip():
        raise PathError("Enter a folder path.")
    p = Path(os.path.expanduser(raw.strip()))
    if not p.is_absolute():
        raise PathError("Use a full (absolute) folder path, e.g. /Users/you/Projects/app.")
    try:
        real = p.resolve(strict=True)
    except (FileNotFoundError, RuntimeError) as e:
        raise PathError("That folder does not exist.") from e
    if not real.is_dir():
        raise PathError("That path is a file, not a folder.")
    if real in EXACT_FORBIDDEN or any(real.is_relative_to(f) for f in TREE_FORBIDDEN):
        raise PathError(
            "System folders and your whole home folder cannot be registered. "
            "Choose a specific project folder."
        )
    if not os.access(real, os.R_OK | os.X_OK):
        raise PathError("The workspace does not have permission to read that folder.")
    return real


def is_sensitive(name: str) -> bool:
    return bool(SENSITIVE.search(name))


def safe_file(root: str, relative: str) -> Path:
    """Resolve a file inside a root, refusing traversal, symlink escapes and secrets."""
    root_real = Path(root).resolve()
    if not relative or Path(relative).is_absolute():
        raise PathError("Invalid file path.")
    candidate = (root_real / relative).resolve()
    if not candidate.is_relative_to(root_real):
        raise PathError("That path is outside the registered folder.")
    if any(part in SKIP_DIRS for part in candidate.relative_to(root_real).parts[:-1]):
        raise PathError("Files in that folder are not indexed.")
    if is_sensitive(candidate.name):
        raise PathError("That file looks like it contains secrets, so it is never read.")
    return candidate


def guess_category(rel: str) -> C:
    low = rel.lower()
    name = Path(low).name
    ext = Path(low).suffix
    rules = [
        (("adr", "decision"), C.ADR),
        (("architecture",), C.ARCHITECTURE),
        (("requirement", "prd"), C.REQUIREMENTS),
        (("brief",), C.BRIEF),
        (("release", "changelog"), C.RELEASE_NOTES),
        (("meeting", "minutes"), C.MEETING_NOTES),
        (("research",), C.RESEARCH),
        (("test",), C.TESTING),
        (("spec",), C.SPECIFICATION),
        (("prototype", "mockup"), C.PROTOTYPE),
        (("report",), C.REPORT),
        (("design",), C.DESIGN),
    ]
    if ext in {".png", ".jpg", ".jpeg", ".svg", ".drawio", ".excalidraw", ".mmd", ".puml"}:
        return C.DIAGRAM
    if ext in {".pptx", ".ppt", ".key", ".odp"}:
        return C.PRESENTATION
    for words, cat in rules:
        if any(w in name for w in words) or any(f"/{w}" in f"/{low}" for w in words):
            return cat
    return C.OTHER


@dataclass
class FoundFile:
    relative_path: str
    size_bytes: int
    modified_at: datetime
    suggested_category: C


def scan(root: str) -> tuple[list[FoundFile], bool]:
    """Walk a root (no symlink following). Returns files and whether the limit truncated it."""
    root_real = Path(root).resolve()
    found: list[FoundFile] = []
    for dirpath, dirnames, filenames in os.walk(root_real, followlinks=False):
        depth = len(Path(dirpath).relative_to(root_real).parts)
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(".") and depth < MAX_DEPTH
        )
        for name in sorted(filenames):
            if name.startswith(".") or is_sensitive(name):
                continue
            full = Path(dirpath) / name
            if full.is_symlink():
                continue
            try:
                st = full.stat()
            except OSError:
                continue
            rel = str(full.relative_to(root_real))
            found.append(
                FoundFile(
                    rel, st.st_size, datetime.fromtimestamp(st.st_mtime, UTC), guess_category(rel)
                )
            )
            if len(found) >= MAX_SCAN_FILES:
                return found, True
    return found, False


def read_text(path: Path) -> str:
    if path.suffix.lower() not in TEXT_EXT:
        raise PathError("Preview is only available for text files.")
    if not path.is_file():
        raise PathError("The file no longer exists at that location.")
    if path.stat().st_size > MAX_PREVIEW:
        raise PathError("The file is too large to preview (over 512 KB).")
    with path.open("r", encoding="utf-8", errors="replace") as fh:  # read-only
        return fh.read()
