"""Walk a repository, exclude noise directories, and map .py files to modules."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

DEFAULT_EXCLUDES = [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "build",
    "dist",
    ".eggs",
    "*.egg-info",
]

DEFAULT_PATTERNS = ["test_*.py", "*_test.py"]

LAYOUT_CHOICES = ("auto", "flat", "src")

_NON_SOURCE_TOP = ("tests", "test", "src")


def is_excluded(name: str, excludes: list[str]) -> bool:
    """True when a directory or file basename matches any exclude pattern."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in excludes)


def iter_py_files(root: Path, excludes: list[str]) -> list[str]:
    """Return sorted POSIX-relative paths of every non-excluded .py file."""
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not is_excluded(d, excludes))
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            if is_excluded(filename, excludes):
                continue
            rel = Path(dirpath).relative_to(root).as_posix()
            found.append(filename if rel == "." else rel + "/" + filename)
    return sorted(found)


def _has_init(path: Path) -> bool:
    return (path / "__init__.py").is_file()


def _top_level_dirs(root: Path, excludes: list[str], skip: tuple[str, ...]) -> list[str]:
    dirs = []
    if not root.is_dir():
        return dirs
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in skip or is_excluded(name, excludes):
            continue
        dirs.append(name)
    return dirs


def detect_layout(root: Path, excludes: list[str]) -> str:
    """Choose ``src`` or ``flat``.

    - src/ has .py files and the root has no top-level packages (outside
      tests/src) -> ``src``.
    - top-level packages exist but src/ has no .py files -> ``flat``.
    - both exist -> ``src`` when a package under src/ shares a name with a
      root package or with the target directory itself, otherwise ``flat``.
    - neither -> ``flat``.
    """
    src_dir = root / "src"
    src_py = iter_py_files(src_dir, excludes) if src_dir.is_dir() else []
    root_pkgs = [
        d
        for d in _top_level_dirs(root, excludes, skip=_NON_SOURCE_TOP)
        if _has_init(root / d)
    ]
    src_pkgs = (
        [d for d in _top_level_dirs(src_dir, excludes, skip=()) if _has_init(src_dir / d)]
        if src_dir.is_dir()
        else []
    )
    if src_py and not root_pkgs:
        return "src"
    if root_pkgs and not src_py:
        return "flat"
    if src_py and root_pkgs:
        target_name = root.name
        if set(src_pkgs) & set(root_pkgs) or target_name in src_pkgs:
            return "src"
        return "flat"
    return "flat"


def module_name_for(relpath: str, layout: str) -> str:
    """Map a repo-relative .py path to a dotted module name ('' if unmappable).

    In ``src`` layout, paths under ``src/`` drop that prefix; every other file
    (tests, root-level scripts) maps relative to the repository root.
    """
    rel = relpath[:-3]  # strip ".py"
    if layout == "src" and rel == "src":
        return ""
    if layout == "src" and rel.startswith("src/"):
        rel = rel[4:]
    dotted = rel.replace("/", ".")
    if dotted.endswith(".__init__"):
        dotted = dotted[: -len(".__init__")]
    elif dotted == "__init__":
        return ""
    return dotted


def matches_pattern(filename: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


class Index:
    """Immutable snapshot of a repository's Python file/module layout."""

    def __init__(
        self,
        root: Path,
        layout: str,
        files: dict[str, str],
        tests: list[str],
        patterns: list[str],
        excludes: list[str],
    ):
        self.root = root
        self.layout = layout
        self.files = files  # relpath (POSIX) -> dotted module
        self.modules = {module: rel for rel, module in files.items()}
        self.tests = tests  # sorted relpaths of discovered test files
        self.test_set = set(tests)
        self.patterns = patterns
        self.excludes = excludes

    def module_of(self, relpath: str) -> str | None:
        return self.files.get(relpath)

    def path_of(self, module: str) -> str | None:
        return self.modules.get(module)

    def is_test(self, relpath: str) -> bool:
        return relpath in self.test_set

    def is_init(self, module: str) -> bool:
        rel = self.modules.get(module)
        return bool(rel) and rel.endswith("__init__.py")

    def package_of(self, module: str) -> str:
        """Dotted package name that relative imports resolve against."""
        if self.is_init(module):
            return module
        return module.rpartition(".")[0]


def build_index(
    root,
    layout: str = "auto",
    excludes: list[str] | None = None,
    patterns: list[str] | None = None,
) -> Index:
    """Index ``root`` (a directory) and return an :class:`Index`.

    ``excludes`` are extra basename patterns appended to the defaults;
    ``patterns`` replace the default test-file patterns.
    """
    root = Path(root)
    all_excludes = DEFAULT_EXCLUDES + list(excludes or [])
    use_patterns = list(patterns) if patterns else list(DEFAULT_PATTERNS)
    if layout not in LAYOUT_CHOICES:
        raise ValueError(f"unknown layout: {layout!r}")
    resolved = detect_layout(root, all_excludes) if layout == "auto" else layout

    candidates: dict[str, tuple[str, bool]] = {}
    for rel in iter_py_files(root, all_excludes):
        module = module_name_for(rel, resolved)
        if not module:
            continue
        candidates[rel] = (module, rel.endswith("__init__.py"))

    # Resolve module-name collisions deterministically: the file under the
    # layout root wins, then packages over plain modules, then lexically.
    def under_layout_root(rel: str) -> bool:
        return resolved != "src" or rel.startswith("src/")

    chosen: dict[str, str] = {}
    for rel in sorted(candidates):
        module, is_pkg = candidates[rel]
        prior = chosen.get(module)
        if prior is None:
            chosen[module] = rel
            continue
        prior_is_under = under_layout_root(prior)
        new_is_under = under_layout_root(rel)
        if new_is_under and not prior_is_under:
            better = rel
        elif prior_is_under and not new_is_under:
            better = prior
        else:
            prior_is_pkg = candidates[prior][1]
            if is_pkg and not prior_is_pkg:
                better = rel
            elif prior_is_pkg and not is_pkg:
                better = prior
            else:
                better = min(prior, rel)
        chosen[module] = better

    files = {rel: module for module, rel in chosen.items()}
    tests = sorted(
        rel for rel in files if matches_pattern(rel.rsplit("/", 1)[-1], use_patterns)
    )
    return Index(
        root=root,
        layout=resolved,
        files=files,
        tests=tests,
        patterns=use_patterns,
        excludes=all_excludes,
    )
