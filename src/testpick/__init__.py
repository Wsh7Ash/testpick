"""testpick: choose the tests that matter for the files you changed.

testpick indexes a Python codebase's import graph with the ``ast`` module,
maps changed files to the tests that (transitively) import them, and emits a
targeted test command. It only reads files; it never executes analyzed code.
"""

__version__ = "0.1.0"


class UsageError(Exception):
    """User-facing error reported on stderr with exit code 2."""
