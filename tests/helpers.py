"""Shared fixtures for testpick's own test suite (not a test module itself)."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE = REPO_ROOT / "examples" / "sample_project"

GIT_AVAILABLE = shutil.which("git") is not None

_IDENTITY = ["-c", "user.name=testpick", "-c", "user.email=testpick@example.invalid"]


def push_git_ceiling(directory: Path):
    """Stop git from ascending above ``directory``; returns a restore callable.

    Temporary test directories may live inside the developer's own git
    repository (for example the home directory), which would make
    "non-repository" scenarios accidentally succeed. The ceiling isolates
    each temp repo from parents without touching anything permanent.
    """
    previous = os.environ.get("GIT_CEILING_DIRECTORIES")
    os.environ["GIT_CEILING_DIRECTORIES"] = str(directory)

    def restore() -> None:
        if previous is None:
            os.environ.pop("GIT_CEILING_DIRECTORIES", None)
        else:
            os.environ["GIT_CEILING_DIRECTORIES"] = previous

    return restore


def write_repo(root: Path, files: dict[str, str]) -> Path:
    """Create (or extend) a repository from a {relpath: content} mapping."""
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def run_cli(*argv: str):
    """Run testpick's main() capturing stdout/stderr; returns (code, out, err)."""
    from testpick.cli import main

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main([arg for arg in argv])
    return code, out.getvalue(), err.getvalue()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result


def git_init_commit_all(repo: Path, message: str) -> str:
    """Init a repo, commit everything, and return the commit SHA."""
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(
        repo,
        "-c",
        "commit.gpgsign=false",
        *_IDENTITY,
        "commit",
        "-q",
        "-m",
        message,
    )
    result = git(repo, "rev-parse", "HEAD")
    return result.stdout.strip()
