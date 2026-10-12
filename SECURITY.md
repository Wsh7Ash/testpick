# Security policy

## Supported versions

Only the latest release line (0.1.x) receives fixes.

## What testpick does with your data

testpick is designed to be safe to point at any repository:

- **It reads files locally.** Python files are opened and parsed with
  `ast.parse`. Code from the analyzed repository is never imported,
  executed, or evaluated - no `exec`, no `eval`, no plugin loading.
- **It runs one subprocess, optionally.** With `--git` (or
  `--git --base REF`) testpick runs `git diff --name-only ...` with the
  target directory as the working directory. No other git subcommands, no
  shell string interpolation, no execution of hooks beyond what a plain
  `git diff` does in your own checkout.
- **No network access.** testpick makes no HTTP/DNS requests and contains
  no telemetry. Offline by construction.
- **No persistence.** Nothing is written outside of stdout/stderr; there is
  no cache directory, config file, or state store.

## Output hygiene

- Reports contain repository-relative paths and module names only.
- Notes and warnings go to stderr, reports to stdout, so piping output into
  another tool cannot accidentally mix diagnostics with data.
- Selection is deterministic; testpick does not embed environment details
  into its output.

## Reporting a vulnerability

Please report security issues privately via the project's GitHub Security
Advisory (or the repository issue tracker if advisories are unavailable),
including:

1. the testpick version and command line;
2. what you expected versus what happened;
3. a minimal reproduction repository or file set.

Do not attach material you are not allowed to share; a synthetic fixture
that reproduces the behavior is enough. You will receive an acknowledgement
and an assessment of the report, and credit is given in the changelog if
you want it.
