# testpick

*I changed these files - which tests should I actually run?*

testpick answers that question for Python repositories. It walks the target
repo, builds its import graph with the standard `ast` module, maps your
changed files to the tests that (transitively) import them, and prints a
targeted test command. `--explain` shows the import chain that connects each
selected test to your change.

- Standard library only: no dependencies, no installation required.
- Reads files locally; it never executes the code it analyzes.
- Flat and `src/` layouts, git or list-file change inputs, three output
  formats, deterministic sorted output.

## Running it

The package lives under `src/`, so put that directory on `PYTHONPATH` and run
`python -m testpick` (PowerShell shown; use `PYTHONPATH=src` in POSIX shells):

```powershell
$env:PYTHONPATH = "src"
python -m testpick --help
python -m testpick examples\sample_project --changed src\shop\pricing.py
```

Changed paths are always relative to the target directory and use the layout
that appears in the repository: for the `src/` layout example project that
means `src\shop\pricing.py` (forward slashes work too). The target directory
itself is the first positional argument.

## Example

The bundled example project has a `src/shop/` package where
`shop/report.py` imports `shop.pricing`, plus four test files. Changing one
source file:

```powershell
$env:PYTHONPATH = "src"
python -m testpick examples\sample_project --changed src\shop\pricing.py --explain
```

produces (verbatim output of the command above):

```text
changed: src/shop/pricing.py
selected 2 test file(s):

tests/test_pricing.py
  reason: import-chain
  chain: tests/test_pricing.py -> shop.pricing (changed)

tests/test_report.py
  reason: import-chain
  chain: tests/test_report.py -> shop.report -> shop.pricing (changed)
```

`tests/test_report.py` is selected transitively: the test imports
`shop.report`, which imports `shop.pricing`. `tests/test_inventory.py` and
`tests/test_utils.py` are not selected because neither imports anything in
the pricing chain.

The same selection as a ready-to-run command:

```text
$ python -m testpick examples\sample_project --changed src\shop\pricing.py --format cmd
python -m unittest tests.test_pricing tests.test_report
```

Run that from the target repository's directory (add `PYTHONPATH=src` there
if the project uses the `src/` layout). In the example project it executes
the 5 selected tests.

## Change inputs

Priority order - the first source present is used:

1. `--changed FILE` - repeatable, one path per flag.
2. `--changed-from LISTFILE` - one path per line, `#` comment lines and blank
   lines are skipped.
3. `--git` - `git diff --name-only HEAD` run inside the target directory.
   With `--base REF` it becomes `git diff --name-only REF HEAD`, i.e. files
   that differ between `REF` and `HEAD` (staged/unstaged working-tree changes
   are not included in that mode).

## Selection rules

| Situation | Result |
| --- | --- |
| changed file is a test file | that test is selected (`reason: direct`) |
| changed source file | every test whose import closure contains its module (`reason: import-chain`) |
| changed non-Python file | nothing affected (reported on stderr) |
| nothing matched | name-similarity fallback: `pkg/mod.py` -> `test_mod.py` / `tests/test_mod.py` (`reason: fallback-name-match`, disable with `--no-fallback`) |
| still nothing and `--all-if-empty` | the whole suite (`reason: all_if_empty`) |

A changed `.py` file that is not part of the index (for example an excluded
or already-deleted path) is reported on stderr and contributes no selection.

## Output formats

- `--format list` (default): sorted test file paths, one per line.
- `--format cmd`: a single command line.
  `--runner unittest` (default) emits
  `python -m unittest tests.test_a tests.test_b` with dotted module paths;
  `--runner pytest` emits `python -m pytest tests/test_a.py tests/test_b.py`.
- `--format json`:
  `{changed, selected: [{path, reason, chain?, fallback}], format, runner, command}`.
- `--explain`: per-test reason and import chain
  (`tests/test_a.py -> pkg.a -> pkg.b (changed)`); with `--format cmd` the
  command is printed first, then the explanation. JSON output always carries
  the `chain` field for `import-chain` reasons.

Notes and warnings go to stderr, so stdout stays pipeable.

## Exit codes

- `0` - tests were selected, or there was legitimately nothing to select.
- `2` - usage error: missing/invalid target, no change input at all,
  `--base` without `--git`, a failing `git diff`, or a bad flag.

## Flags

```text
target                  repository directory to index
--changed FILE          changed file (repeatable)
--changed-from LISTFILE read changed paths from a file
--git                   read changed paths from git diff
--base REF              with --git: diff REF against HEAD
--layout auto|flat|src  module layout (default: auto)
--exclude PATTERN       extra exclude pattern (repeatable, added to defaults)
--pattern GLOB          test file pattern (repeatable; default: test_*.py *_test.py)
--format list|cmd|json  output format (default: list)
--runner unittest|pytest  runner for --format cmd (default: unittest)
--explain               show reasons and import chains
--no-fallback           disable the name-similarity fallback
--all-if-empty          select the whole suite when nothing matched
```

Default excluded directories: `.git`, `.venv`, `venv`, `__pycache__`,
`node_modules`, `.tox`, `.mypy_cache`, `.pytest_cache`, `build`, `dist`,
`.eggs`, `*.egg-info`.

Layout detection (`--layout auto`): prefer `src/` when it holds the `.py`
files and the repository root has no top-level packages; when both exist,
prefer `src/` if a package under `src/` shares its name with a root package
or with the target directory. Tests at `tests/` are mapped relative to the
repository root regardless of layout.

## Limitations

- Python only. Other languages are ignored.
- Only static imports are resolved. Dynamic imports (`importlib`,
  plugin entry points, `__import__`, string-based or reflectively loaded
  modules) are NOT resolved, so tests that load a module at runtime can be
  missed. This is the main false-negative source.
- `from pkg import *` records the package but not the individual names.
- The name-similarity fallback is a heuristic: it can pair a test with an
  unrelated module that merely shares a name, and it can miss renamed tests.
  It is marked in the output (`fallback: true`) and can be disabled.
- No coverage weighting, flakiness history, or timing data: selection is
  purely structural (import graph + file changes).
- Files that fail to parse are skipped with a warning; their dependencies
  are invisible to the graph.

## Using it in pre-commit and CI

Pre-push hook that runs only the tests affected by staged files (POSIX):

```sh
#!/bin/sh
# .git/hooks/pre-push - chmod +x
set -e
TARGET=/path/to/target
TESTPICK=/path/to/testpick
git -C "$TARGET" diff --name-only HEAD > /tmp/testpick-changed.txt
SELECTED=$(cd "$TESTPICK" && PYTHONPATH=src python -m testpick "$TARGET" \
    --changed-from /tmp/testpick-changed.txt --format list)
if [ -n "$SELECTED" ]; then
    cd "$TARGET"
    python -m unittest $(printf '%s\n' "$SELECTED" | sed 's#/#.#g; s#\.py$##')
fi
```

PowerShell version of the same three stages:

```powershell
# pre-push: stage 1 - changed files, stage 2 - selection, stage 3 - run
git -C C:\path\to\target diff --name-only HEAD | Set-Content $env:TEMP\testpick-changed.txt
$env:PYTHONPATH = "src"
$selected = python -m testpick C:\path\to\target --changed-from $env:TEMP\testpick-changed.txt --format list
if ($selected) {
    Push-Location C:\path\to\target
    python -m unittest @(($selected -replace '/','.') -replace '\.py$','')
    Pop-Location
}
```

CI job that runs only what a job's changed files touch (GitHub Actions):

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- name: Select tests for this change
  run: |
    PYTHONPATH=$GITHUB_WORKSPACE/src python -m testpick . \
      --changed-from <(git diff --name-only ${{ github.event.pull_request.base.sha }} HEAD) \
      --format cmd > cmd.txt
- name: Run selected tests
  run: |
    CMD=$(cat cmd.txt)
    if [ -n "$CMD" ]; then cd . && eval "$CMD"; else echo "no tests selected"; fi
```

Because `--git --base <sha>` is built in, the selection step can also be
written as `python -m testpick . --git --base ${{ github.event.pull_request.base.sha }} --format cmd`
when the checkout has full history.

## Security notes

- testpick parses files with `ast.parse`; it never imports or executes code
  from the repository being analyzed.
- Network access: none. No telemetry, no remote lookups.
- `--git` shells out to exactly one command, `git diff --name-only ...`,
  run inside the target directory.
- Output is deterministic and contains only repository-relative paths.

See SECURITY.md for the full policy.

## Development

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -t . -v
```

`tests/__init__.py` inserts the repository's `src` directory into `sys.path`,
so no environment variables or package installs are needed to run the suite.
The suite uses only `unittest` (no pytest) and runs on Python 3.10+; CI runs
it on 3.12.

Project documents: docs/PROJECT_SPEC.md, docs/ARCHITECTURE.md,
docs/USAGE.md. Captured command outputs live in results/ and RESULTS.md.

## License

MIT - see LICENSE. Copyright (c) 2026 Wsh7Ash.
