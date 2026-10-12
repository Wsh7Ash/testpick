"""Build the directed import graph (importer -> imported) with ``ast``.

Only static imports are resolved, and only to modules that exist inside the
indexed repository. Files are parsed, never executed.
"""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path


class Graph:
    """Directed graph of dotted-module dependencies plus query helpers."""

    def __init__(self, edges: dict[str, set[str]], errors: list[str]):
        self.edges = edges  # module -> set of in-repo modules it imports
        self.errors = errors  # relpaths that failed to parse

    def closure(self, module: str) -> set[str]:
        """Modules reachable from ``module`` (transitive, cycle-safe).

        The starting module itself is not part of the result unless a cycle
        leads back to it.
        """
        visited: set[str] = set()
        stack = list(self.edges.get(module, ()))
        while stack:
            node = stack.pop()
            if node == module or node in visited:
                continue
            visited.add(node)
            stack.extend(self.edges.get(node, ()))
        visited.discard(module)
        return visited

    def chain(self, start: str, target: str) -> list[str] | None:
        """Shortest path ``[start, ..., target]`` (inclusive), or None.

        Neighbours are visited in sorted order so equal-length chains are
        deterministic.
        """
        if start == target:
            return [start]
        previous: dict[str, str | None] = {start: None}
        queue: deque[str] = deque([start])
        while queue:
            node = queue.popleft()
            for neighbour in sorted(self.edges.get(node, ())):
                if neighbour in previous:
                    continue
                previous[neighbour] = node
                if neighbour == target:
                    path = [neighbour]
                    while previous[path[-1]] is not None:
                        path.append(previous[path[-1]])  # type: ignore[arg-type]
                    path.reverse()
                    return path
                queue.append(neighbour)
        return None


def _prefixes(module: str):
    parts = module.split(".")
    for i in range(1, len(parts) + 1):
        yield ".".join(parts[:i])


def _collect(tree: ast.AST) -> list[tuple[int, str | None, list[str]]]:
    """Return (level, module, names) for every import statement."""
    found: list[tuple[int, str | None, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((0, alias.name, []))
        elif isinstance(node, ast.ImportFrom):
            names = [alias.name for alias in node.names]
            found.append((node.level, node.module, names))
    return found


def build_graph(index) -> Graph:
    """Parse every indexed file and resolve its in-repo imports."""
    edges: dict[str, set[str]] = {module: set() for module in index.modules}
    errors: list[str] = []

    for rel, module in sorted(index.files.items()):
        path = Path(index.root, rel)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=rel)
        except (SyntaxError, ValueError, OSError):
            errors.append(rel)
            continue

        targets: set[str] = set()

        def add(candidate: str | None) -> None:
            if not candidate or candidate == module:
                return
            for prefix in _prefixes(candidate):
                if prefix in index.modules and prefix != module:
                    targets.add(prefix)

        for level, mod, names in _collect(tree):
            if level == 0:
                base = mod or ""
            else:
                package = index.package_of(module)
                if not package:
                    continue  # relative import outside any package: unresolvable
                parts = package.split(".")
                if level - 1 > len(parts):
                    continue  # relative import escapes the repository root
                kept = parts[: len(parts) - (level - 1)]
                base = ".".join(kept)
                if mod:
                    base = base + "." + mod if base else mod
            add(base or None)
            for name in names:
                if name == "*":
                    continue  # star import: individual targets are unknown
                add(base + "." + name if base else name)

        edges[module] = targets

    return Graph(edges, errors)
