"""Tests for repository walking, layout detection, and module mapping."""

import tempfile
import unittest
from pathlib import Path

from tests.helpers import write_repo

from testpick.indexer import (
    DEFAULT_EXCLUDES,
    build_index,
    detect_layout,
    module_name_for,
)


class ModuleMappingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_flat_layout_maps_modules(self):
        write_repo(
            self.root,
            {
                "pkg/__init__.py": "",
                "pkg/mod.py": "x = 1\n",
                "pkg/sub/__init__.py": "",
                "pkg/sub/deep.py": "y = 2\n",
                "test_mod.py": "def test_x():\n    pass\n",
            },
        )
        index = build_index(self.root, layout="flat")
        self.assertEqual(index.layout, "flat")
        self.assertEqual(index.module_of("pkg/mod.py"), "pkg.mod")
        self.assertEqual(index.module_of("pkg/sub/deep.py"), "pkg.sub.deep")
        self.assertEqual(index.module_of("test_mod.py"), "test_mod")

    def test_src_layout_strips_src_prefix(self):
        write_repo(
            self.root,
            {
                "src/pkg/mod.py": "x = 1\n",
                "tests/test_mod.py": "def test_x():\n    pass\n",
            },
        )
        index = build_index(self.root, layout="src")
        self.assertEqual(index.layout, "src")
        self.assertEqual(index.module_of("src/pkg/mod.py"), "pkg.mod")
        self.assertEqual(index.module_of("tests/test_mod.py"), "tests.test_mod")
        self.assertEqual(index.path_of("pkg.mod"), "src/pkg/mod.py")

    def test_init_py_maps_to_package_name(self):
        write_repo(self.root, {"pkg/__init__.py": "", "pkg/mod.py": "x = 1\n"})
        index = build_index(self.root, layout="flat")
        self.assertEqual(index.module_of("pkg/__init__.py"), "pkg")
        self.assertTrue(index.is_init("pkg"))

    def test_root_init_py_is_skipped(self):
        write_repo(self.root, {"__init__.py": "", "mod.py": "x = 1\n"})
        index = build_index(self.root, layout="flat")
        self.assertNotIn("__init__.py", index.files)
        self.assertEqual(index.module_of("mod.py"), "mod")

    def test_module_name_for_helpers(self):
        self.assertEqual(module_name_for("a/b/c.py", "flat"), "a.b.c")
        self.assertEqual(module_name_for("src/a/b.py", "src"), "a.b")
        self.assertEqual(module_name_for("src/a/__init__.py", "src"), "a")
        self.assertEqual(module_name_for("a/__init__.py", "flat"), "a")

    def test_collision_layout_root_wins(self):
        write_repo(
            self.root,
            {
                "shop/pricing.py": "root = True\n",
                "src/shop/__init__.py": "",
                "src/shop/pricing.py": "src = True\n",
            },
        )
        index = build_index(self.root, layout="src")
        self.assertEqual(index.module_of("src/shop/pricing.py"), "shop.pricing")
        self.assertNotIn("shop/pricing.py", index.files)


class LayoutDetectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_auto_src_when_root_has_no_packages(self):
        write_repo(
            self.root,
            {"src/pkg/__init__.py": "", "tests/test_a.py": "pass\n"},
        )
        self.assertEqual(detect_layout(self.root, list(DEFAULT_EXCLUDES)), "src")

    def test_auto_flat_when_only_root_package(self):
        write_repo(
            self.root,
            {"pkg/__init__.py": "", "pkg/mod.py": "x = 1\n", "tests/test_a.py": "pass\n"},
        )
        self.assertEqual(detect_layout(self.root, list(DEFAULT_EXCLUDES)), "flat")

    def test_auto_both_prefers_src_on_package_name_match(self):
        write_repo(
            self.root,
            {
                "app/__init__.py": "old = True\n",
                "src/app/__init__.py": "new = True\n",
            },
        )
        self.assertEqual(detect_layout(self.root, list(DEFAULT_EXCLUDES)), "src")

    def test_auto_both_flat_without_match(self):
        write_repo(
            self.root,
            {
                "oldpkg/__init__.py": "",
                "src/newpkg/__init__.py": "",
            },
        )
        self.assertEqual(detect_layout(self.root, list(DEFAULT_EXCLUDES)), "flat")

    def test_auto_both_prefers_src_when_target_dir_name_matches(self):
        target = self.root / "sample"
        write_repo(
            target,
            {
                "other/__init__.py": "",
                "src/sample/__init__.py": "",
            },
        )
        self.assertEqual(detect_layout(target, list(DEFAULT_EXCLUDES)), "src")

    def test_explicit_layout_skips_detection(self):
        write_repo(self.root, {"src/pkg/__init__.py": "", "pkg2/__init__.py": ""})
        index = build_index(self.root, layout="flat")
        self.assertEqual(index.layout, "flat")


class ExclusionAndDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_default_excludes_are_honored(self):
        write_repo(
            self.root,
            {
                "pkg/keep.py": "x = 1\n",
                ".venv/lib/site.py": "x = 1\n",
                "venv/lib/site.py": "x = 1\n",
                "pkg/__pycache__/mod.cpython-314.py": "x = 1\n",
                "node_modules/dep/index.py": "x = 1\n",
                ".tox/py314/lib/mod.py": "x = 1\n",
                ".mypy_cache/mod.py": "x = 1\n",
                ".pytest_cache/pytest.py": "x = 1\n",
                "build/gen.py": "x = 1\n",
                "dist/gen.py": "x = 1\n",
                ".eggs/gen.py": "x = 1\n",
                "pkg.egg-info/gen.py": "x = 1\n",
                ".git/hooks/pre.py": "x = 1\n",
            },
        )
        index = build_index(self.root, layout="flat")
        self.assertEqual(sorted(index.files), ["pkg/keep.py"])

    def test_custom_exclude_adds_to_defaults(self):
        write_repo(
            self.root,
            {
                "pkg/keep.py": "x = 1\n",
                "vendor/lib.py": "x = 1\n",
                ".venv/lib/site.py": "x = 1\n",
            },
        )
        index = build_index(self.root, layout="flat", excludes=["vendor"])
        self.assertEqual(sorted(index.files), ["pkg/keep.py"])

    def test_default_test_patterns(self):
        write_repo(
            self.root,
            {
                "tests/__init__.py": "",
                "tests/test_alpha.py": "pass\n",
                "tests/beta_test.py": "pass\n",
                "tests/testish.py": "pass\n",
                "tests/helper.py": "pass\n",
                "test_gamma.py": "pass\n",
            },
        )
        index = build_index(self.root, layout="flat")
        self.assertEqual(
            index.tests,
            [
                "test_gamma.py",
                "tests/beta_test.py",
                "tests/test_alpha.py",
            ],
        )

    def test_custom_test_pattern(self):
        write_repo(
            self.root,
            {
                "tests/check_alpha.py": "pass\n",
                "tests/test_beta.py": "pass\n",
            },
        )
        index = build_index(self.root, layout="flat", patterns=["check_*.py"])
        self.assertEqual(index.tests, ["tests/check_alpha.py"])

    def test_non_python_files_not_indexed(self):
        write_repo(
            self.root,
            {
                "README.md": "# hi\n",
                "data/products.json": "{}\n",
                "pkg/mod.py": "x = 1\n",
            },
        )
        index = build_index(self.root, layout="flat")
        self.assertEqual(sorted(index.files), ["pkg/mod.py"])


if __name__ == "__main__":
    unittest.main()
