# Contributing

Thanks for considering a contribution to testpick.

## Ground rules

- Python standard library only. No third-party runtime or test
  dependencies (the target machines are PEP 668 managed and CI installs
  nothing).
- ASCII source files.
- Never add absolute paths, machine-specific values, or secrets.
- Keep the analyzed code sacred: testpick must parse files, never execute
  code from the repository it is inspecting. No network access.

## Development setup

No installation is required. From the repository root (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -t . -v
```

The test suite injects `src/` into `sys.path` itself (see
`tests/__init__.py`), so even `python -m unittest discover -s tests -t .`
works without setting anything.

## Running a single test module

```powershell
$env:PYTHONPATH = "src"
python -m unittest tests.test_select -v
```

## What to test

Add tests alongside the feature:

- `tests/test_indexer.py` - walking, excludes, layout detection, mapping;
- `tests/test_graph.py` - import resolution, closure, cycles, chains;
- `tests/test_select.py` - selection rules;
- `tests/test_report.py` - output shapes;
- `tests/test_gitdiff.py` - list files and git mode (guarded with
  `unittest.skipUnless(shutil.which("git"))`);
- `tests/test_cli.py` - exit codes, flags, end-to-end behavior.

Prefer small temporary repositories built with `tests.helpers.write_repo`
over fixtures on disk. Extend `examples/sample_project` only when a new
demo scenario is needed, and keep its existing fixture files stable - the
README and `results/` captures quote them.

## Style

- Keep modules small and single-purpose; follow the layout described in
  docs/ARCHITECTURE.md.
- Deterministic output is a feature: sort anything you iterate.
- Notes/warnings go to stderr; stdout carries only the report.

## Checks before submitting

1. `python -m unittest discover -s tests -t . -v` passes (exit 0).
2. If you changed demo-visible behavior, re-run the demo commands from
   README.md / docs/USAGE.md and refresh `results/` and RESULTS.md with the
   real new output.
3. Update CHANGELOG.md under a new version heading.

## Reporting bugs

Open an issue with the command you ran, the expected and actual output,
exit code, and (if possible) a minimal repository that reproduces the
problem. See SECURITY.md for security reports.
