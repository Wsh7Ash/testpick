"""CLI-level tests: exit codes, formats, flags, and git mode end to end."""

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import (
    GIT_AVAILABLE,
    SAMPLE,
    git,
    git_init_commit_all,
    push_git_ceiling,
    run_cli,
    write_repo,
)


class ExitCodeTests(unittest.TestCase):
    def test_exit_0_with_selection(self):
        code, out, err = run_cli(str(SAMPLE), "--changed", "src/shop/pricing.py")
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(), ["tests/test_pricing.py", "tests/test_report.py"]
        )

    def test_exit_0_non_python_change_is_legitimately_none(self):
        code, out, err = run_cli(str(SAMPLE), "--changed", "README.md")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("not a Python file", err)
        self.assertIn("no tests selected", err)

    def test_exit_0_module_without_tests(self):
        code, out, err = run_cli(
            str(SAMPLE), "--changed", "src/shop/shipping.py", "--no-fallback"
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("no tests selected", err)

    def test_exit_2_target_not_found(self):
        code, out, err = run_cli("no/such/dir", "--changed", "a.py")
        self.assertEqual(code, 2)
        self.assertIn("target directory not found", err)

    def test_exit_2_target_not_a_directory(self):
        code, out, err = run_cli(str(SAMPLE / "README.md"), "--changed", "a.py")
        self.assertEqual(code, 2)
        self.assertIn("not a directory", err)

    def test_exit_2_no_change_input(self):
        code, out, err = run_cli(str(SAMPLE))
        self.assertEqual(code, 2)
        self.assertIn("no changed files given", err)

    def test_exit_2_base_requires_git(self):
        code, out, err = run_cli(str(SAMPLE), "--base", "main")
        self.assertEqual(code, 2)
        self.assertIn("--base requires --git", err)

    def test_exit_2_argparse_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli(str(SAMPLE), "--changed", "a.py", "--format", "xml")
        self.assertEqual(ctx.exception.code, 2)

    def test_exit_2_missing_target_argument(self):
        with self.assertRaises(SystemExit) as ctx:
            run_cli()
        self.assertEqual(ctx.exception.code, 2)


class FlagTests(unittest.TestCase):
    def test_format_json(self):
        code, out, err = run_cli(
            str(SAMPLE), "--changed", "src/shop/pricing.py", "--format", "json"
        )
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["changed"], ["src/shop/pricing.py"])
        self.assertEqual(
            [i["path"] for i in payload["selected"]],
            ["tests/test_pricing.py", "tests/test_report.py"],
        )
        self.assertEqual(payload["format"], "json")
        self.assertEqual(payload["runner"], "unittest")

    def test_format_cmd(self):
        code, out, err = run_cli(
            str(SAMPLE), "--changed", "src/shop/pricing.py", "--format", "cmd"
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            out.strip(), "python -m unittest tests.test_pricing tests.test_report"
        )

    def test_format_cmd_pytest_runner(self):
        code, out, err = run_cli(
            str(SAMPLE),
            "--changed",
            "src/shop/pricing.py",
            "--format",
            "cmd",
            "--runner",
            "pytest",
        )
        self.assertEqual(code, 0)
        self.assertEqual(
            out.strip(),
            "python -m pytest tests/test_pricing.py tests/test_report.py",
        )

    def test_explain_flag(self):
        code, out, err = run_cli(
            str(SAMPLE), "--changed", "src/shop/pricing.py", "--explain"
        )
        self.assertEqual(code, 0)
        self.assertIn(
            "chain: tests/test_report.py -> shop.report -> shop.pricing (changed)",
            out,
        )
        self.assertIn("reason: import-chain", out)

    def test_explain_with_cmd_appends_chain(self):
        code, out, err = run_cli(
            str(SAMPLE),
            "--changed",
            "src/shop/pricing.py",
            "--format",
            "cmd",
            "--explain",
        )
        self.assertEqual(code, 0)
        first_line = out.splitlines()[0]
        self.assertEqual(first_line, "python -m unittest tests.test_pricing tests.test_report")
        self.assertIn("chain:", out)

    def test_no_fallback_flag(self):
        code, out, err = run_cli(
            str(SAMPLE), "--changed", "src/shop/utils.py", "--no-fallback"
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("no tests selected", err)

    def test_fallback_default_enabled(self):
        code, out, err = run_cli(str(SAMPLE), "--changed", "src/shop/utils.py")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "tests/test_utils.py")

    def test_all_if_empty_flag(self):
        code, out, err = run_cli(
            str(SAMPLE), "--changed", "src/shop/shipping.py", "--all-if-empty"
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 4)

    def test_changed_wins_over_changed_from(self):
        with tempfile.TemporaryDirectory() as tmp:
            listfile = Path(tmp) / "changed.txt"
            listfile.write_text("src/shop/inventory.py\n", encoding="utf-8")
            code, out, err = run_cli(
                str(SAMPLE),
                "--changed",
                "src/shop/pricing.py",
                "--changed-from",
                str(listfile),
            )
        self.assertEqual(code, 0)
        self.assertEqual(
            out.splitlines(), ["tests/test_pricing.py", "tests/test_report.py"]
        )

    def test_changed_from_listfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            listfile = Path(tmp) / "changed.txt"
            listfile.write_text(
                "# demo\nsrc/shop/inventory.py\n", encoding="utf-8"
            )
            code, out, err = run_cli(str(SAMPLE), "--changed-from", str(listfile))
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "tests/test_inventory.py")

    def test_custom_pattern_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                {
                    "pkg/__init__.py": "",
                    "pkg/mod.py": "value = 1\n",
                    "tests/check_mod.py": "from pkg.mod import value\n",
                    "tests/test_mod.py": "from pkg.mod import value\n",
                },
            )
            code, out, err = run_cli(
                str(root),
                "--layout",
                "flat",
                "--changed",
                "pkg/mod.py",
                "--pattern",
                "check_*.py",
            )
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "tests/check_mod.py")

    def test_layout_flag_flat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                {
                    "src/pkg/__init__.py": "",
                    "src/pkg/mod.py": "value = 1\n",
                    "tests/test_mod.py": "from pkg.mod import value\n",
                },
            )
            code, out, err = run_cli(
                str(root), "--layout", "flat", "--changed", "src/pkg/mod.py"
            )
            # flat layout maps src/pkg/mod.py to src.pkg.mod; the import in the
            # test resolves to pkg.mod, so nothing matches and fallback finds
            # no test named test_mod.py under tests/... (it does): fallback.
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), "tests/test_mod.py")


@unittest.skipUnless(GIT_AVAILABLE, "git is not installed")
class GitModeEndToEndTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(push_git_ceiling(self.root.parent))

    def _make_repo(self):
        write_repo(
            self.root,
            {
                "pkg/__init__.py": "",
                "pkg/mod.py": "value = 1\n",
                "tests/test_mod.py": "from pkg.mod import value\n",
                "tests/test_other.py": "assert True\n",
            },
        )
        git_init_commit_all(self.root, "initial")

    def test_git_mode_selects_tests_for_modified_source(self):
        self._make_repo()
        (self.root / "pkg" / "mod.py").write_text("value = 2\n", encoding="utf-8")
        code, out, err = run_cli(str(self.root), "--git")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "tests/test_mod.py")

    def test_git_mode_with_base_ref(self):
        self._make_repo()
        base = git(self.root, "rev-parse", "HEAD").stdout.strip()
        (self.root / "tests" / "test_other.py").write_text(
            "assert 1 == 1\n", encoding="utf-8"
        )
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
            "touch test_other",
        )
        code, out, err = run_cli(str(self.root), "--git", "--base", base)
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "tests/test_other.py")

    def test_git_mode_non_repo_exit_2(self):
        write_repo(self.root, {"a.py": "value = 1\n"})
        probe = git(self.root, "rev-parse", "--show-toplevel", check=False)
        if probe.returncode == 0:
            self.skipTest("temp directory already sits inside a git repository")
        code, out, err = run_cli(str(self.root), "--git")
        self.assertEqual(code, 2)
        self.assertIn("git diff failed", err)


class OutputHygieneTests(unittest.TestCase):
    def test_notes_go_to_stderr_not_stdout(self):
        code, out, err = run_cli(str(SAMPLE), "--changed", "README.md", "--format", "json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["selected"], [])
        self.assertIn("not a Python file", err)

    def test_output_is_deterministic(self):
        first = run_cli(str(SAMPLE), "--changed", "src/shop/pricing.py")
        second = run_cli(str(SAMPLE), "--changed", "src/shop/pricing.py")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
