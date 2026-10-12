"""Tests for changed-file inputs: list files and git diff mode."""

import tempfile
import unittest
from pathlib import Path

from tests.helpers import (
    GIT_AVAILABLE,
    git,
    git_init_commit_all,
    push_git_ceiling,
    write_repo,
)

from testpick import UsageError
from testpick.gitdiff import changed_from_git, changed_from_listfile


class ListfileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_comments_and_blank_lines_skipped(self):
        listfile = self.root / "changed.txt"
        listfile.write_text(
            "# changed files\n"
            "\n"
            "src/pkg/mod.py\n"
            "   \n"
            "  tests/test_mod.py  \n"
            "# trailing comment\n",
            encoding="utf-8",
        )
        self.assertEqual(
            changed_from_listfile(listfile),
            ["src/pkg/mod.py", "tests/test_mod.py"],
        )

    def test_missing_listfile_raises_usage_error(self):
        with self.assertRaises(UsageError):
            changed_from_listfile(self.root / "missing.txt")


@unittest.skipUnless(GIT_AVAILABLE, "git is not installed")
class GitDiffTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(push_git_ceiling(self.root.parent))

    def test_default_diff_against_head(self):
        write_repo(
            self.root,
            {"a.py": "value = 1\n", "b.py": "value = 2\n", "pkg/mod.py": "x = 1\n"},
        )
        git_init_commit_all(self.root, "initial")
        (self.root / "a.py").write_text("value = 11\n", encoding="utf-8")
        (self.root / "pkg" / "mod.py").write_text("x = 2\n", encoding="utf-8")
        changed = changed_from_git(self.root)
        self.assertEqual(sorted(changed), ["a.py", "pkg/mod.py"])

    def test_base_ref_diff(self):
        write_repo(self.root, {"a.py": "value = 1\n", "b.py": "value = 2\n"})
        first = git_init_commit_all(self.root, "initial")
        (self.root / "b.py").write_text("value = 22\n", encoding="utf-8")
        git(self.root, "add", "-A")
        git(
            self.root,
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=testpick",
            "-c",
            "user.email=testpick@example.invalid",
            "commit",
            "-q",
            "-m",
            "change b",
        )
        changed = changed_from_git(self.root, base=first)
        self.assertEqual(changed, ["b.py"])

    def test_no_changes_returns_empty(self):
        write_repo(self.root, {"a.py": "value = 1\n"})
        git_init_commit_all(self.root, "initial")
        self.assertEqual(changed_from_git(self.root), [])

    def test_non_repo_raises_usage_error(self):
        write_repo(self.root, {"a.py": "value = 1\n"})
        probe = git(self.root, "rev-parse", "--show-toplevel", check=False)
        if probe.returncode == 0:
            self.skipTest("temp directory already sits inside a git repository")
        with self.assertRaises(UsageError):
            changed_from_git(self.root)


if __name__ == "__main__":
    unittest.main()
