# Architecture

testpick is a small pipeline of pure-ish stages. Each stage is a module in
`src/testpick/`; `cli.py` is the only one that prints or exits.

```text
changed inputs                 index                  graph
(--changed /                    (indexer.py)           (graph.py)
 --changed-from /              walk + excludes        ast.parse per file
 --git)          --->          layout detection   --->  absolute/relative
(gitdiff.py)                   file -> module           import edges
     |                         module -> file           closure + chain
     v                              |                        |
  list[str] ------------------------+------------------------+
                                          |
                                          v
                                    select (select.py)
                                    direct / import-chain /
                                    fallback / all_if_empty
                                          |
                                          v
                                    report (report.py)
                                    list | cmd | json | explain
                                          |
                                          v
                                    cli.py -> stdout + exit code
```

## Module responsibilities

### `indexer.py`

- `DEFAULT_EXCLUDES` / `DEFAULT_PATTERNS`: the built-in directory excludes
  and test-file globs.
- `iter_py_files(root, excludes)`: `os.walk` with directory pruning; every
  directory/file basename is matched against the exclude patterns with
  `fnmatch` (so `*.egg-info` works). Returns sorted POSIX-relative paths.
- `detect_layout(root, excludes)`: implements the `auto` rules (see README);
  a top-level directory only counts as a root package if it contains
  `__init__.py`, so `tests/`, `docs/`, and `examples/` never influence the
  decision.
- `module_name_for(relpath, layout)`: `pkg/mod.py` -> `pkg.mod`;
  `src/` prefix stripped in `src` layout; `pkg/__init__.py` -> `pkg`;
  root-level `__init__.py` has no name and is skipped.
- `build_index(...)`: produces an immutable `Index` with
  `files` (path -> module), `modules` (module -> path), `tests` (sorted
  discovered test paths), patterns, excludes. Module-name collisions are
  resolved deterministically: the file under the layout root wins, then
  packages over plain modules, then the lexicographically smaller path.
- `Index.package_of(module)`: the dotted package that relative imports
  resolve against (the module itself for `__init__.py`, the parent package
  otherwise).

### `graph.py`

- `build_graph(index)` parses each indexed file with `ast.parse`
  (`SyntaxError` -> recorded in `Graph.errors`, never fatal) and collects
  every `ast.Import` / `ast.ImportFrom` node via `ast.walk`.
- Absolute `import a.b` and `from a.b import c` add edges to `a.b` and to
  every prefix (`a`) that exists in the index - importing a submodule
  executes its package initializers.
- Relative imports resolve the level against `index.package_of`; levels that
  escape the repository root, or relative imports from files outside any
  package, are skipped. `from . import name` also tries `<pkg>.name` so
  submodule imports are captured. Star imports record the package only.
- Only modules present in the index receive edges; third-party imports
  (`requests`, etc.) are ignored by construction.
- `Graph.closure(module)`: iterative DFS with a visited set (cycle guard);
  the start module is excluded from its own closure.
- `Graph.chain(start, target)`: BFS shortest path with sorted neighbours, so
  equal-length chains are deterministic; returns `None` when unreachable.

### `select.py`

`select(index, graph, changed, use_fallback, all_if_empty)` applies the
rules in the fixed priority order documented in README:

1. changed test file -> `direct`;
2. changed source -> every test whose precomputed closure contains its
   module -> `import-chain` with the displayed chain
   `[test path, ..., changed module]`;
3. non-`.py` or unindexed changes -> note, no selection;
4. nothing selected -> name-similarity fallback (the changed file's stem is
   substituted into each test pattern and checked at the repository root and
   under `tests/`) -> `fallback-name-match`, `fallback: true`;
5. still nothing -> `--all-if-empty` selects the whole suite.

Paths are normalized (`\` -> `/`, `./` and leading `/` stripped) before any
lookup. Output order is sorted by path; notes accumulate for stderr.

### `gitdiff.py`

- `changed_from_listfile`: one path per line, blank and `#` lines skipped.
- `changed_from_git(repo, base)`:
  `git diff --name-only HEAD`, or `git diff --name-only <base> HEAD` with
  `--base`. Non-zero exit raises `UsageError` (CLI exit code 2).

### `report.py`

- `render_list`: sorted paths.
- `render_cmd` / `build_command`: `python -m unittest <dotted modules>` or
  `python -m pytest <paths>`; dotted names come from `index.module_of` so
  they are correct under the `src/` layout; `None`/empty when nothing is
  selected.
- `render_json`: fixed key order
  `changed, selected[{path, reason, chain?, fallback}], format, runner,
  command`.
- `render_explain`: `changed:` header, count, then per test `reason:` and
  `chain:` lines with ` (changed)` on the final node, plus short notes for
  `direct`, `fallback-name-match`, and `all_if_empty`.

### `cli.py`

- `build_parser()`: every flag from the spec, `argparse` choices for
  enums; argparse errors exit 2 natively.
- `gather_changed()`: priority `--changed` > `--changed-from` > `--git`;
  no input at all is a `UsageError`.
- `main()`: validates target and `--base`/`--git` pairing, builds index and
  graph, prints parse warnings and selection notes to **stderr**, renders to
  stdout, returns `0` (selection or legitimate empty result) or `2`
  (`UsageError`).

### `__main__.py`

Three lines so `python -m testpick` works with the package on
`PYTHONPATH=src`.

## Data invariants

- `Index.files` keys are POSIX-relative paths; values are unique dotted
  module names.
- `Graph.edges` only contains modules from `Index.modules`.
- Selected test paths always exist in `Index.test_set`.
- stdout carries only the rendered report; everything else goes to stderr.
- Rendering the same inputs twice is byte-identical (sorted walks, sorted
  BFS neighbours, fixed JSON key order).

## Why stdlib only

`ast` gives the import graph without importing anything, `fnmatch` gives
glob excludes, `argparse` gives the CLI, `subprocess` gives the single git
call. There is nothing to install, which keeps the tool usable on PEP 668
managed machines and in minimal CI images.
