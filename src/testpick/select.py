"""Turn a list of changed files into a ranked set of test files."""

from __future__ import annotations

from dataclasses import dataclass, field

REASON_DIRECT = "direct"
REASON_IMPORT = "import-chain"
REASON_FALLBACK = "fallback-name-match"
REASON_ALL = "all_if_empty"


@dataclass
class Selected:
    path: str  # repo-relative POSIX path of the test file
    reason: str
    chain: list[str] | None = None  # [test path, ..., changed module]
    fallback: bool = False


@dataclass
class Selection:
    changed: list[str]
    selected: list[Selected] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def paths(self) -> list[str]:
        return [item.path for item in self.selected]


def normalize_path(raw: str) -> str:
    """Normalize a user-supplied changed path to repo-relative POSIX form."""
    path = raw.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def _display_chain(test_path: str, chain: list[str]) -> list[str]:
    """Show the test as its file path, then dotted modules along the chain."""
    return [test_path] + chain[1:]


def select(
    index,
    graph,
    changed: list[str],
    *,
    use_fallback: bool = True,
    all_if_empty: bool = False,
) -> Selection:
    """Apply the selection rules in priority order.

    1. a changed test file selects itself (reason ``direct``);
    2. a changed source file selects every test whose import closure contains
       its module (reason ``import-chain``);
    3. changed non-.py files select nothing (reported via notes);
    4. when nothing matched, name-similarity fallback
       (``pkg/mod.py`` -> ``test_mod.py`` / ``tests/test_mod.py``) unless
       disabled with ``use_fallback=False``;
    5. when still empty and ``all_if_empty``, select the whole suite.
    """
    normalized = [normalize_path(raw) for raw in changed]
    selection = Selection(changed=normalized)
    chosen: dict[str, Selected] = {}

    # Rule 1: a changed test file is included directly.
    for rel in normalized:
        if rel in index.test_set:
            chosen[rel] = Selected(path=rel, reason=REASON_DIRECT)

    # Precompute each test's transitive import closure once.
    closures: dict[str, set[str]] = {}
    for test_rel in index.tests:
        module = index.files.get(test_rel)
        if module is not None:
            closures[test_rel] = graph.closure(module)

    # Rule 2: changed source -> tests whose closure contains its module.
    for rel in normalized:
        if rel in chosen or rel in index.test_set:
            continue
        if not rel.endswith(".py"):
            selection.notes.append(
                f"changed file {rel} is not a Python file; no tests affected"
            )
            continue
        module = index.files.get(rel)
        if module is None:
            selection.notes.append(
                f"changed file {rel} not found in index; skipping"
            )
            continue
        for test_rel in index.tests:
            if test_rel in chosen:
                continue
            if module in closures.get(test_rel, ()):
                chain = graph.chain(index.files[test_rel], module)
                if chain is None:
                    continue
                chosen[test_rel] = Selected(
                    path=test_rel,
                    reason=REASON_IMPORT,
                    chain=_display_chain(test_rel, chain),
                )

    # Rule 4: name-similarity fallback, only when nothing matched so far.
    if not chosen and use_fallback:
        for rel in normalized:
            if not rel.endswith(".py") or rel in index.test_set:
                continue
            if rel not in index.files:
                continue
            stem = rel.rsplit("/", 1)[-1][: -len(".py")]
            candidates: list[str] = []
            for pattern in index.patterns:
                name = pattern.replace("*", stem)
                candidates.append(name)
                candidates.append("tests/" + name)
            for candidate in sorted(set(candidates)):
                if candidate in index.test_set:
                    chosen[candidate] = Selected(
                        path=candidate, reason=REASON_FALLBACK, fallback=True
                    )

    # Rule 5: fall back to the whole suite on request.
    if not chosen and all_if_empty:
        for test_rel in index.tests:
            chosen[test_rel] = Selected(path=test_rel, reason=REASON_ALL)

    selection.selected = [chosen[path] for path in sorted(chosen)]
    if not selection.selected:
        selection.notes.append("no tests selected")
    return selection
