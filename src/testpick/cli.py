"""Command-line interface for testpick.

Exit codes: 0 = tests selected or legitimately none, 2 = usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from testpick import UsageError
from testpick.gitdiff import changed_from_git, changed_from_listfile
from testpick.graph import build_graph
from testpick.indexer import LAYOUT_CHOICES, build_index
from testpick.report import (
    FORMAT_CHOICES,
    RUNNER_CHOICES,
    render_cmd,
    render_explain,
    render_json,
    render_list,
)
from testpick.select import select

DEFAULT_EXCLUDE_NOTE = "extra exclude patterns (repeatable, added to the defaults)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="testpick",
        description=(
            "Pick the tests that matter: index a Python repo's import graph, "
            "map changed files to the tests that (transitively) import them, "
            "and print a targeted test command."
        ),
    )
    parser.add_argument("target", help="repository (or project) directory to index")
    parser.add_argument(
        "--changed",
        action="append",
        metavar="FILE",
        help="changed file, relative to the target directory (repeatable)",
    )
    parser.add_argument(
        "--changed-from",
        metavar="LISTFILE",
        help="file with one changed path per line ('#' comment lines allowed)",
    )
    parser.add_argument(
        "--git",
        action="store_true",
        help="read changed files from git diff (default: git diff --name-only HEAD)",
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="with --git: diff against REF instead of the working tree "
        "(git diff --name-only REF HEAD)",
    )
    parser.add_argument(
        "--layout",
        choices=LAYOUT_CHOICES,
        default="auto",
        help="module layout: auto (default), flat, or src",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        metavar="PATTERN",
        help=DEFAULT_EXCLUDE_NOTE,
    )
    parser.add_argument(
        "--pattern",
        action="append",
        metavar="GLOB",
        help="test file name pattern (repeatable; default: test_*.py *_test.py)",
    )
    parser.add_argument(
        "--format",
        choices=FORMAT_CHOICES,
        default="list",
        help="output format: list (default), cmd, json",
    )
    parser.add_argument(
        "--runner",
        choices=RUNNER_CHOICES,
        default="unittest",
        help="runner for --format cmd: unittest (default) or pytest",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="show the reason (and import chain) for every selected test",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="disable the name-similarity fallback when nothing matches",
    )
    parser.add_argument(
        "--all-if-empty",
        action="store_true",
        help="select the whole suite when no test matches the changes",
    )
    return parser


def gather_changed(args: argparse.Namespace) -> list[str]:
    """Inputs in priority order: --changed > --changed-from > --git."""
    if args.changed:
        return list(args.changed)
    if args.changed_from:
        return changed_from_listfile(args.changed_from)
    if args.git:
        return changed_from_git(args.target, args.base)
    raise UsageError(
        "no changed files given: use --changed, --changed-from, or --git"
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.base and not args.git:
            raise UsageError("--base requires --git")
        target = Path(args.target)
        if not target.exists():
            raise UsageError(f"target directory not found: {args.target}")
        if not target.is_dir():
            raise UsageError(f"target is not a directory: {args.target}")

        changed = gather_changed(args)
        index = build_index(
            target,
            layout=args.layout,
            excludes=args.exclude,
            patterns=args.pattern,
        )
        graph = build_graph(index)
        for rel in graph.errors:
            print(f"testpick: warning: could not parse {rel}", file=sys.stderr)
        selection = select(
            index,
            graph,
            changed,
            use_fallback=not args.no_fallback,
            all_if_empty=args.all_if_empty,
        )
        for note in selection.notes:
            print(f"testpick: {note}", file=sys.stderr)

        fmt = args.format
        if fmt == "json":
            output = render_json(selection, args.runner, index)
        elif fmt == "cmd":
            output = render_cmd(selection, args.runner, index)
            if args.explain and output:
                output = output + "\n\n" + render_explain(selection)
            elif args.explain:
                output = render_explain(selection)
        else:  # list
            output = render_explain(selection) if args.explain else render_list(selection)

        if output:
            print(output)
        return 0
    except UsageError as exc:
        print(f"testpick: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
