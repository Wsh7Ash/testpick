# Project specification: testpick

## Name

testpick

## Category

programmer-productivity

## Target user

Python developers and CI maintainers with a growing test suite who need to
know which tests to run after a change, without running everything and
without guessing.

## Problem

As repositories grow, running the full test suite on every change becomes
slow, while picking tests by hand is error-prone: developers forget which
tests cover a module, and CI either wastes minutes on the whole suite or
runs too little and misses regressions. The information needed to decide -
which tests (transitively) import which modules - already exists in the
code, but nothing surfaces it at the moment of a change.

## Solution

testpick indexes the target repository's import graph with the standard
library `ast` module (parsing only; code is never executed), maps each
changed file to the tests whose import closure contains it, and emits a
ready-to-run test command. `--explain` shows the import chain that connects
every selected test to the change, so the selection is auditable rather than
a black box.

## Core workflow

1. Point testpick at a repository (flat or `src/` layout).
2. Supply the changed files: `--changed` flags, a `--changed-from` list file,
   or `--git [--base REF]`.
3. Receive the minimal test list (`--format list`), a runnable command
   (`--format cmd`), machine-readable JSON (`--format json`), or the
   selection with import chains (`--explain`).
4. Run the emitted command in the target repository.

## Must-have features

- Repository walk excluding `.git`, `.venv`, `venv`, `__pycache__`,
  `node_modules`, `.tox`, `.mypy_cache`, `.pytest_cache`, `build`, `dist`,
  `.eggs`, `*.egg-info` (configurable with `--exclude`).
- Layout detection: `--layout auto|flat|src`, including the `src/` preference
  rules when both layouts are present.
- Dotted module names for every `.py` file, with packages via `__init__.py`.
- Import resolution via `ast`: absolute imports, relative imports resolved
  against the file's package, in-repo modules only; directed
  importer-to-imported graph; per-test transitive closure with cycle guard.
- Test discovery matching `test_*.py` / `*_test.py`, configurable with
  `--pattern`.
- Change inputs in priority order: repeatable `--changed`,
  `--changed-from` list file with `#` comments, `--git` with optional
  `--base REF`.
- Selection rules: changed test selects itself; changed source selects every
  test whose closure contains its module; non-Python changes affect nothing
  (reported clearly); name-similarity fallback (`pkg/mod.py` ->
  `test_mod.py`/`tests/test_mod.py`, marked `fallback:true`, disable with
  `--no-fallback`); `--all-if-empty` selects the whole suite with
  `reason: all_if_empty`.
- Output formats `list` (sorted, default), `cmd` (`--runner unittest`
  dotted paths by default, `--runner pytest` paths), `json`
  (`{changed, selected:[{path, reason, chain?, fallback}], format, runner,
  command?}`).
- `--explain` with import chains
  (`tests/test_a.py -> pkg.a -> pkg.b (changed)`), `direct`, or
  `fallback-name-match`, in both text and JSON (`chain`).
- Exit codes: 0 for a selection or a legitimate empty result, 2 for usage
  errors.
- Deterministic, sorted output.

## Nice-to-have features

- Running the emitted command automatically (deliberately out of scope:
  testpick selects, the user's runner executes).
- Coverage weighting, flakiness data, or test timing - not included.
- Non-Python languages - not included.
- Parallel or cached indexing - not needed at current scale.

## Stack

- Python 3.14 (developed and tested here), `requires-python >= 3.10`.
- Standard library only: `ast`, `argparse`, `fnmatch`, `os`, `pathlib`,
  `subprocess`, `json`, `dataclasses`. No third-party dependencies.
- Tests: `unittest` with `python -m unittest discover -s tests -t .`
  (no pytest, no installs).
- Windows + PowerShell development environment; CI on Ubuntu with
  setup-python 3.12.

## Test strategy

Unit tests against temporary repositories plus end-to-end tests against the
committed `examples/sample_project` (101 tests total):

- module mapping for flat and `src/` layouts, packages, `__init__.py`,
  collisions, root `__init__` skipping;
- layout auto-detection rules;
- default and custom exclusions; default and custom test patterns;
- absolute, relative, star, and out-of-repo import resolution; parse-error
  tolerance; transitive closure; cycle termination; chain finding;
- every selection rule, including the required transitive case
  (`test_report -> shop.report -> shop.pricing`), fallback on/off,
  `--all-if-empty`, non-Python changes, path normalization;
- `list`/`cmd`/`json` shapes, `--explain` chains, JSON key order and
  `fallback` flags, determinism;
- git mode in throwaway `tempfile` repositories guarded by
  `unittest.skipUnless(shutil.which("git"))`, including `--base`;
- CLI exit codes 0 and 2, input priority, notes on stderr.

## Demo/result strategy

Real, observed outputs are committed under `results/`:

- `demo-list.txt`, `demo-cmd.txt`, `demo-explain.txt`, `demo-json.json` -
  produced by the documented `python -m testpick` commands against
  `examples/sample_project`;
- `demo-git.txt` - a multi-step `--git` / `--git --base` session in a
  throwaway repository created under the OS temp directory (path redacted to
  `<temp-repo>`; the project repository is never a git repository).

`RESULTS.md` records the exact commands, observed counts, and exit codes.
The README quotes the `--explain` transcript verbatim.

## Safety considerations

- The analyzed repository's code is never imported or executed; only
  `ast.parse` and file reads are used.
- No network access, no telemetry.
- The only subprocess is `git diff --name-only ...` in `--git` mode, run
  inside the target directory.
- Output contains repository-relative paths only; no absolute paths or
  secrets are read into results.
- Failed parses degrade to a warning instead of executing anything.

## Definition of done

- All required files present: README, MIT LICENSE, `.gitignore`,
  `src/testpick/*` modules, `pyproject.toml` (0.1.0, no deps), `tests/`,
  `docs/` (spec, architecture, usage), `examples/sample_project/`,
  `results/` captures, `RESULTS.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, `.github/workflows/ci.yml`.
- `python -m unittest discover -s tests -t . -v` passes with at least 35
  tests and exit code 0, no installs and no env vars.
- Every demo command in RESULTS.md has been executed and its output and
  exit code recorded verbatim.
- Git-mode tests run (not skipped) against a temp repository.
- README limitations are honest: Python only, no dynamic-import resolution,
  heuristic fallback, no coverage weighting.
