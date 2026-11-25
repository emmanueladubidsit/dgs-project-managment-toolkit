"""Confirmed text-file writes into a project's connected folder (ADR 0011).

Used by the browser extension's "Add to file": the user previews the change, then confirms.
Rules: only inside the connected folder (symlinks resolved, no `..` or absolute paths); never
secret-looking files or dependency/VCS folders; text only, at most 512 KB; refused if the file
changed since the preview; written atomically (temporary file, then rename)."""

import difflib
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from app.services import files

MAX_BYTES = 512 * 1024
MAX_DIFF_LINES = 400


class WriteError(ValueError):
    pass


@dataclass
class Target:
    root: Path
    path: Path
    relative: str


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve(root: str, relative: str) -> Target:
    rel = (relative or "").strip().replace("\\", "/")
    if not rel or rel.startswith(("/", "~")) or ":" in rel.split("/")[0]:
        raise WriteError("Use a path relative to the project folder, e.g. src/app.py.")
    parts = PurePosixPath(rel).parts
    if any(p in ("..", ".") for p in parts) or rel.endswith("/"):
        raise WriteError("The path must name a file inside the project folder (no '..').")
    if any(p in files.SKIP_DIRS for p in parts[:-1]):
        raise WriteError(
            f"Files inside “{next(p for p in parts if p in files.SKIP_DIRS)}” are never written."
        )
    if files.is_sensitive(parts[-1]):
        raise WriteError("That file name looks like it holds secrets, so it is never written.")
    base = Path(root).resolve()
    candidate = base.joinpath(*parts)
    # Resolve the deepest existing ancestor (and the file itself if present): a symlink must not
    # lead outside the folder.
    probe = candidate
    while not probe.exists() and probe != base:
        probe = probe.parent
    if not probe.resolve().is_relative_to(base):
        raise WriteError("That path leads outside the project folder.")
    if candidate.is_symlink() or (
        candidate.exists() and not candidate.resolve().is_relative_to(base)
    ):
        raise WriteError("Links are never followed when writing.")
    if candidate.exists() and not candidate.is_file():
        raise WriteError("That path is a folder, not a file.")
    return Target(root=base, path=candidate, relative="/".join(parts))


def _current(t: Target) -> str | None:
    if not t.path.exists():
        return None
    if t.path.stat().st_size > MAX_BYTES:
        raise WriteError("The existing file is larger than 512 KB, so it is not changed here.")
    raw = t.path.read_bytes()
    if b"\0" in raw:
        raise WriteError("The existing file is not a text file, so it is not changed here.")
    return raw.decode("utf-8", errors="replace")


def _check_content(content: str) -> None:
    if "\0" in content:
        raise WriteError("Only text can be written.")
    if len(content.encode("utf-8")) > MAX_BYTES:
        raise WriteError("The content is larger than 512 KB.")


def preview(root: str, relative: str, content: str) -> dict:
    _check_content(content)
    t = resolve(root, relative)
    current = _current(t)
    diff = list(
        difflib.unified_diff(
            (current or "").splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{t.relative}" if current is not None else "/dev/null",
            tofile=f"b/{t.relative}",
        )
    )
    truncated = len(diff) > MAX_DIFF_LINES
    return {
        "path": t.relative,
        "exists": current is not None,
        "will_create": current is None,
        "unchanged": current == content,
        "diff": "".join(diff[:MAX_DIFF_LINES]) + ("\n… (diff truncated)\n" if truncated else ""),
        "current_sha256": sha256(current) if current is not None else None,
    }


def write(root: str, relative: str, content: str, expected_sha256: str | None) -> dict:
    """Write after a preview. `expected_sha256` is the preview's `current_sha256` (None for a
    new file); a mismatch means the file changed meanwhile, so nothing is written."""
    _check_content(content)
    t = resolve(root, relative)
    current = _current(t)
    now_hash = sha256(current) if current is not None else None
    if now_hash != expected_sha256:
        raise WriteError(
            "The file changed since the preview (or was created meanwhile). Preview again."
        )
    t.path.parent.mkdir(parents=True, exist_ok=True)
    if not t.path.parent.resolve().is_relative_to(t.root):
        raise WriteError("That path leads outside the project folder.")
    fd, tmp = tempfile.mkstemp(dir=t.path.parent, prefix=".dgs-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
        # Keep an existing file's permissions; new files get the usual rw-r--r--.
        os.chmod(tmp, t.path.stat().st_mode & 0o777 if current is not None else 0o644)
        os.replace(tmp, t.path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return {"path": t.relative, "created": current is None, "bytes": len(content.encode("utf-8"))}
