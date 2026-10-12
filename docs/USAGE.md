# Usage

```text
python -m testpick TARGET [options]
```

`TARGET` is the repository (or project) directory to index. Because the
package lives in `src/`, run it with `PYTHONPATH=src` from the testpick
checkout:

```powershell
$env:PYTHONPATH = "src"
python -m testpick --help
```

All changed paths are relative to `TARGET` and use the paths as they appear
in that repository (`src\shop\pricing.py` or `src/shop/pricing.py` for a
`src/` layout project).

## Choosing the changed files

Priority order: the first input source present is used.

| Flag | Meaning |
| --- | --- |
| `--changed FILE` | one changed path; repeat the flag for more files |
| `--changed-from LISTFILE` | one path per line; blank lines and lines starting with `#` are skipped |
| `--git` | run `git diff --name-only HEAD` inside TARGET |
| `--git --base REF` | run `git diff --name-only REF HEAD` inside TARGET |

`--base` without `--git` is a usage error (exit 2). If none of the three
sources is given, testpick exits 2 with a message.

Note the difference between the git modes: the default form shows working
tree and staged changes relative to `HEAD`; `--base REF` shows the
difference between two committed states (the current `HEAD` tree versus
`REF`).

## Selection rules

1. A changed test file selects itself: `reason: direct`.
2. A changed source file selects every test whose transitive import closure
   contains the file's module: `reason: import-chain`, with `chain` recorded.
3. Changed non-Python files select nothing; a note is printed on stderr.
4. If nothing matched, name-similarity fallback pairs `pkg/mod.py` with
   `test_mod.py` or `tests/test_mod.py` (built from the active
   `--pattern` globs): `reason: fallback-name-match`, `fallback: true`.
   Disable with `--no-fallback`.
5. If still empty, `--all-if-empty` selects every discovered test with
   `reason: all_if_empty`.

## Formats

### `--format list` (default)

```powershell
python -m testpick examples\sample_project --changed src\shop\pricing.py
```

```text
tests/test_pricing.py
tests/test_report.py
```

Sorted, one repo-relative path per line. An empty selection prints nothing
(stdout) and explains why (stderr).

### `--format cmd`

```powershell
python -m testpick examples\sample_project --changed src\shop\pricing.py --format cmd
```

```text
python -m unittest tests.test_pricing tests.test_report
```

With `--runner pytest`:

```text
python -m pytest tests/test_pricing.py tests/test_report.py
```

Run the command from the target repository's directory. For a `src/` layout
target, set `PYTHONPATH=src` there first so the package under `src/` is
importable.

### `--format json`

```powershell
python -m testpick examples\sample_project --changed src\shop\pricing.py --format json
```

```json
{
  "changed": [
    "src/shop/pricing.py"
  ],
  "selected": [
    {
      "path": "tests/test_pricing.py",
      "reason": "import-chain",
      "chain": [
        "tests/test_pricing.py",
        "shop.pricing"
      ],
      "fallback": false
    },
    {
      "path": "tests/test_report.py",
      "reason": "import-chain",
      "chain": [
        "tests/test_report.py",
        "shop.report",
        "shop.pricing"
      ],
      "fallback": false
    }
  ],
  "format": "json",
  "runner": "unittest",
  "command": "python -m unittest tests.test_pricing tests.test_report"
}
```

`chain` is present only for `import-chain` reasons. `command` is `null`
when nothing is selected.

### `--explain`

```powershell
python -m testpick examples\sample_project --changed src\shop\pricing.py --explain
```

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

With `--format cmd --explain`, the command is printed first, followed by
the same explanation.

## Worked examples

Non-Python change - no tests affected (exit 0):

```powershell
python -m testpick examples\sample_project --changed README.md
```

```text
(testpick: changed file README.md is not a Python file; no tests affected)
(testpick: no tests selected)
```

Module with no matching tests, fallback disabled (exit 0, empty stdout):

```powershell
python -m testpick examples\sample_project --changed src\shop\shipping.py --no-fallback
```

Name-similarity fallback (`shop/utils.py` is not imported by any test, but
`tests/test_utils.py` matches by name):

```powershell
python -m testpick examples\sample_project --changed src\shop\utils.py --explain
```

```text
changed: src/shop/utils.py
selected 1 test file(s):

tests/test_utils.py
  reason: fallback-name-match
  note: selected by name similarity, not by imports
```

Whole suite when nothing matches:

```powershell
python -m testpick examples\sample_project --changed src\shop\shipping.py --all-if-empty
```

Git mode (from the target repository, or pass a target path):

```powershell
python -m testpick . --git
python -m testpick . --git --base origin/main
```

List file:

```text
# changed files for the pricing fix
src/shop/pricing.py
tests/test_report.py
```

```powershell
python -m testpick . --changed-from changed.txt --format json
```

## Layout, excludes, patterns

```powershell
python -m testpick . --layout src            # force src/ mapping
python -m testpick . --layout flat           # force flat mapping
python -m testpick . --exclude generated     # add to the default excludes
python -m testpick . --pattern "check_*.py"  # replace the test globs
```

`--exclude` and `--pattern` are repeatable.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | tests selected, or legitimately none (non-Python change, no matches, empty diff) |
| 2 | usage error: bad/missing target, no change input, `--base` without `--git`, failing `git diff`, invalid flag |

## Exit behavior tips

- Notes (`testpick: ...`) always go to stderr; only the report goes to
  stdout, so `--format json` output can be piped straight into a parser.
- Output is deterministic: the same inputs always produce byte-identical
  results, which makes testpick safe to cache in CI.
