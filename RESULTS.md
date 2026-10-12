# RESULTS - testpick 0.1.0

All values below are real observations from this machine
(2026-10-12, Python 3.14.3, git 2.55.0.windows.3, Windows PowerShell).
No pip installs were performed at any point. Commands were run from the
project root with `$env:PYTHONPATH = "src"` unless noted.

## 1. Files created (top level)

```text
.github/workflows/ci.yml
.gitignore
CHANGELOG.md
CONTRIBUTING.md
LICENSE
README.md
RESULTS.md
SECURITY.md
docs/            PROJECT_SPEC.md, ARCHITECTURE.md, USAGE.md
examples/        sample_project/ (src/shop + tests + README.md)
pyproject.toml
results/         demo-list.txt, demo-cmd.txt, demo-explain.txt,
                 demo-json.json, demo-git.txt
src/testpick/    __init__.py, __main__.py, cli.py, indexer.py, graph.py,
                 select.py, gitdiff.py, report.py
tests/           __init__.py, helpers.py, test_indexer.py, test_graph.py,
                 test_select.py, test_report.py, test_gitdiff.py, test_cli.py
```

45 committed files total. The project directory is NOT a git repository
(it was never `git init`ed; the orchestrator owns git).

## 2. Test suite

Command:

```powershell
python -m unittest discover -s tests -t . -v
```

Observed result:

```text
Ran 101 tests in 3.911s
OK
```

- Exit code: **0**
- Failures: 0, errors: 0, skipped: 0
- Per module: test_cli.py 26, test_select.py 19, test_indexer.py 17,
  test_report.py 17, test_graph.py 16, test_gitdiff.py 6 (total 101)
- Coverage of required areas: module mapping (flat + src, packages,
  `__init__.py`, collisions), layout auto-detection, default/custom
  excludes, default/custom patterns, absolute/relative/star import
  resolution, transitive closure, cycle guard, chains, every selection
  rule (direct, source, non-Python, fallback, no-fallback, all-if-empty),
  list/cmd/json shapes, `--explain` chains, git mode in temp repos, CLI
  exit codes 0 and 2.
- `tests/__init__.py` inserts the repo `src/` into `sys.path`; no env vars
  or installs are needed.

Sample project's own suite (run from `examples/sample_project` with
`PYTHONPATH=src`):

```text
Ran 9 tests in 0.051s
OK          exit=0
```

## 3. Demo commands

All stdout below is verbatim; notes go to stderr as shown.

| # | Command | Observed output (stdout / stderr) | Exit |
|---|---------|-----------------------------------|------|
| 1 | `python -m testpick examples\sample_project --changed src\shop\pricing.py` | `tests/test_pricing.py` / `tests/test_report.py` | 0 |
| 2 | same + `--explain` | `changed: src/shop/pricing.py` / `selected 2 test file(s):` with chains `tests/test_pricing.py -> shop.pricing (changed)` and `tests/test_report.py -> shop.report -> shop.pricing (changed)` | 0 |
| 3 | same + `--format cmd` | `python -m unittest tests.test_pricing tests.test_report` | 0 |
| 4 | same + `--format json` | JSON with `changed`, 2 `selected` entries (reason `import-chain`, chains, `fallback: false`), `format: json`, `runner: unittest`, `command` | 0 |
| 5 | `python -m testpick examples\sample_project --changed README.md` | stderr: `testpick: changed file README.md is not a Python file; no tests affected` + `testpick: no tests selected`; stdout empty | 0 |
| 6 | `python -m testpick examples\sample_project --changed src\shop\shipping.py --no-fallback` | stderr: `testpick: no tests selected`; stdout empty | 0 |
| 7 | `python -m testpick examples\sample_project` (no change input) | stderr: `testpick: error: no changed files given: use --changed, --changed-from, or --git` | 2 |
| 8 | `python -m testpick examples\sample_project --changed src\shop\utils.py --explain` (fallback demo) | `tests/test_utils.py` with `reason: fallback-name-match` | 0 |
| 9 | `python -m testpick examples\sample_project --changed src\shop\shipping.py --all-if-empty` | all 4 test files, reason `all_if_empty` | 0 |

The emitted command from #3 was executed from `examples/sample_project`
(with `PYTHONPATH=src`): `Ran 5 tests ... OK`, exit 0.

Captured files (written by the commands above, not hand-edited):

- `results/demo-list.txt` - output of command #1
- `results/demo-cmd.txt` - output of command #3
- `results/demo-explain.txt` - output of command #2
- `results/demo-json.json` - output of command #4 (parses with `json.load`)
- `results/demo-git.txt` - git-mode session (section 4)

## 4. Git-mode tests

Unit/integration git tests: **ran, not skipped** (final suite shows
`skipped=0`).

- `tests/test_gitdiff.py` - `git diff --name-only HEAD` in a `tempfile`
  repo, `--base REF` diff, empty diff, non-repository error, list-file
  parsing (6 tests).
- `tests/test_cli.py::GitModeEndToEndTests` - `--git` selecting a test for
  a modified source file, `--git --base`, non-repo exit 2 (3 tests).
  All are guarded with `unittest.skipUnless(shutil.which("git"))`; git is
  present, so none skipped.

The developer's home directory is itself a git repository, which would make
the "non-repository" cases falsely succeed; the tests set
`GIT_CEILING_DIRECTORIES` to the temp directory's parent so each temp repo
is isolated. This changed no product code.

Live demo (`results/demo-git.txt`) run in a throwaway repository created
under the OS temp directory; the testpick project directory was never
`git init`ed. Redaction: the temp directory path appears only as
`<temp-repo>` (hard rule: no absolute paths in committed files); command
outputs, the commit SHA, and all exit codes are verbatim.

| Step | Command | Output | Exit |
|------|---------|--------|------|
| clean tree | `python -m testpick . --git` | `testpick: no tests selected` | 0 |
| `pkg/core.py` modified | `python -m testpick . --git` | `tests/test_core.py` | 0 |
| change committed (clean again) | `python -m testpick . --git` | `testpick: no tests selected` | 0 |
| `--git --base <initial>` | `git diff --name-only <initial> HEAD` semantics | `tests/test_core.py` | 0 |

## 5. Deviations / blockers

Deviations (all additive, none remove required behavior):

1. `src/testpick/__main__.py` added - the spec's mandated commands use
   `python -m testpick`, which requires `__main__.py`; the listed module
   set did not include it.
2. `examples/sample_project/tests/__init__.py` added - makes the emitted
   `python -m unittest tests.test_pricing ...` command reliably runnable
   from the example directory.
3. `tests/helpers.py` added - shared fixtures (`write_repo`, `run_cli`,
   git helpers); unittest discovery (`test*.py`) does not treat it as a
   test module.
4. `results/demo-git.txt` redacts the temp path to `<temp-repo>` (see
   section 4) to satisfy the no-absolute-paths rule.
5. Changed-path convention: for the `src/`-layout example, the changed file
   is passed exactly as it appears in the repo (`src\shop\pricing.py` /
   `src/shop/pricing.py`), documented in README and docs/USAGE.md.

Blockers: none. Verification summary - suite 101/101 pass (exit 0),
all demo exit codes as specified (0 for selections/legitimate empty,
2 for usage errors), git-mode tests executed rather than skipped.
