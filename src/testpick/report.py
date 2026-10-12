"""Render a selection as list, command, json, or explain output."""

from __future__ import annotations

import json

from testpick.select import (
    REASON_ALL,
    REASON_DIRECT,
    REASON_FALLBACK,
    REASON_IMPORT,
    Selection,
)

FORMAT_CHOICES = ("list", "cmd", "json")
RUNNER_CHOICES = ("unittest", "pytest")


def dotted_path(relpath: str) -> str:
    """``tests/test_a.py`` -> ``tests.test_a``."""
    return relpath[: -len(".py")].replace("/", ".")


def build_command(selection: Selection, runner: str, index) -> str | None:
    """The shell command that runs exactly the selected tests (None if empty)."""
    if not selection.selected:
        return None
    if runner == "pytest":
        paths = " ".join(item.path for item in selection.selected)
        return f"python -m pytest {paths}"
    modules = " ".join(
        index.module_of(item.path) or dotted_path(item.path)
        for item in selection.selected
    )
    return f"python -m unittest {modules}"


def render_list(selection: Selection) -> str:
    """Sorted test file paths, one per line."""
    return "\n".join(selection.paths)


def render_cmd(selection: Selection, runner: str, index) -> str:
    command = build_command(selection, runner, index)
    return command if command else ""


def render_json(selection: Selection, runner: str, index) -> str:
    items = []
    for item in selection.selected:
        entry: dict[str, object] = {"path": item.path, "reason": item.reason}
        if item.chain is not None:
            entry["chain"] = item.chain
        entry["fallback"] = item.fallback
        items.append(entry)
    payload = {
        "changed": selection.changed,
        "selected": items,
        "format": "json",
        "runner": runner,
        "command": build_command(selection, runner, index),
    }
    return json.dumps(payload, indent=2)


def render_explain(selection: Selection) -> str:
    """Human-readable per-test reasons and import chains."""
    changed = ", ".join(selection.changed) if selection.changed else "(none)"
    lines = [f"changed: {changed}", f"selected {len(selection.selected)} test file(s):"]
    for item in selection.selected:
        lines.append("")
        lines.append(item.path)
        lines.append(f"  reason: {item.reason}")
        if item.reason == REASON_IMPORT and item.chain:
            chain = list(item.chain)
            chain[-1] = chain[-1] + " (changed)"
            lines.append("  chain: " + " -> ".join(chain))
        elif item.reason == REASON_DIRECT:
            lines.append("  note: this test file was itself changed")
        elif item.reason == REASON_FALLBACK:
            lines.append("  note: selected by name similarity, not by imports")
        elif item.reason == REASON_ALL:
            lines.append("  note: selected because the suite was requested via --all-if-empty")
    return "\n".join(lines)
