# Changelog

All notable changes to this project are documented in this file.

## 0.1.0 - 2026-10-12

Initial release.

- Import-graph indexing with the standard library `ast` module: absolute
  and relative imports, in-repo modules only, transitive per-test closure
  with cycle guard, shortest import chains for `--explain`.
- Layout detection (`auto` / `flat` / `src`) with `__init__.py`-aware
  package mapping and deterministic collision resolution.
- Configurable directory excludes (defaults for `.git`, virtualenvs,
  caches, `build`, `dist`, `*.egg-info`) and test-file patterns
  (`test_*.py`, `*_test.py`).
- Change inputs: repeatable `--changed`, `--changed-from` list files with
  `#` comments, `--git` with optional `--base REF`.
- Selection rules: direct test change, import-chain selection, clear
  reporting for non-Python changes, name-similarity fallback
  (`--no-fallback` to disable), `--all-if-empty`.
- Output formats: `list`, `cmd` (`unittest` dotted paths or `pytest`
  paths), `json`, plus `--explain` chains in text and JSON.
- Exit codes: 0 for selection or legitimate empty results, 2 for usage
  errors; deterministic sorted output; notes on stderr.
- 101 unit/integration tests on `unittest`; example project with a
  transitive-selection fixture; captured demo outputs under `results/`.
