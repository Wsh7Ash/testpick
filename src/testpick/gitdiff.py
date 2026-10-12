"""Collect changed files from a git diff or a list file."""

from __future__ import annotations

import subprocess
from pathlib import Path

from testpick import UsageError


def changed_from_listfile(listfile) -> list[str]:
    """Read one path per line; blank lines and ``#`` comment lines are skipped."""
    path = Path(listfile)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise UsageError(f"cannot read changed-from list: {path} ({exc})") from exc
    changed: list[str] = []
    for line in text.splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        changed.append(entry)
    return changed


def changed_from_git(repo, base: str | None = None) -> list[str]:
    """Names of files that differ from HEAD (or from ``base``).

    - no base: ``git diff --name-only HEAD``
    - with base: ``git diff --name-only <base> HEAD``

    Only the diff is queried; no repository code is ever executed.
    """
    command = ["git", "diff", "--name-only"]
    if base:
        command.append(base)
    command.append("HEAD")
    try:
        result = subprocess.run(
            command,
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise UsageError(f"cannot run git: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        message = detail[-1] if detail else f"exit code {result.returncode}"
        raise UsageError(f"git diff failed in {repo}: {message}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]
