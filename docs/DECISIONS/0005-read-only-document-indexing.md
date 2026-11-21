# ADR 0005 — Documents are indexed read-only, inside registered folders only

- **Status:** Accepted · 21 November 2026

## Context

The brief requires linking documents where they already live, supporting multiple project
directories, never moving, deleting, overwriting or modifying files without approval, and
validating paths.

## Decision

- The user registers folders explicitly (`document_roots`). The resolved real path is stored.
  `/`, the home folder itself, `/Users` and `/Volumes` are refused, and so is anything inside
  system areas (`/System`, `/Library`, `/usr`, `/etc`, `/private`, `/var`…).
- Every file access is resolved — symlinks included — and must remain inside the registered
  root (`services/files.py: safe_file`). Absolute paths, `..` traversal and symlink escapes are
  refused with `invalid_path`.
- Scans walk the tree without following symlinks, skip hidden files and dependency/build folders,
  and **never list or read files that look like secrets** (`.env*`, keys, certificates,
  `credentials`, `secret`, `.netrc`, `.npmrc`…).
- The code only ever opens files for reading. Text previews are limited to known text types up to
  512 KB. Deleting a document record or unregistering a folder never touches the file system.
- Links (`http(s)://` only — `javascript:` and `file:` are rejected) and short in-app notes cover
  documents that do not live in a registered folder.

## Consequences

- Safe to point at real project folders; worst case is an index that is out of date (files moved
  are flagged *not found* and a re-scan refreshes metadata).
- The backend must run on the same machine as the files (true for this local-first app). A cloud
  deployment would need an upload or sync model instead.
