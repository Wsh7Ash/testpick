"""Tests for every selection rule against the sample project."""

import tempfile
import unittest
from pathlib import Path

from tests.helpers import SAMPLE, write_repo

from testpick.graph import build_graph
from testpick.indexer import build_index
from testpick.select import (
    REASON_ALL,
    REASON_DIRECT,
    REASON_FALLBACK,
    REASON_IMPORT,
    normalize_path,
    select,
)


def sample_selection(*changed, **kwargs):
    index = build_index(SAMPLE, layout="auto")
    graph = build_graph(index)
    return select(index, graph, list(changed), **kwargs)


class SampleProjectSelectionTests(unittest.TestCase):
    """The demo scenario: changing pricing must reach test_report transitively."""

    def test_changed_test_selects_itself_directly(self):
        selection = sample_selection("tests/test_pricing.py")
        self.assertEqual(selection.paths, ["tests/test_pricing.py"])
        self.assertEqual(selection.selected[0].reason, REASON_DIRECT)
        self.assertIsNone(selection.selected[0].chain)

    def test_source_change_selects_importing_tests(self):
        selection = sample_selection("src/shop/pricing.py")
        self.assertEqual(
            selection.paths, ["tests/test_pricing.py", "tests/test_report.py"]
        )
        self.assertTrue(all(s.reason == REASON_IMPORT for s in selection.selected))

    def test_transitive_chain_selects_test_report(self):
        """test_report -> shop.report -> shop.pricing (the required case)."""
        selection = sample_selection("src/shop/pricing.py")
        report = next(s for s in selection.selected if s.path == "tests/test_report.py")
        self.assertEqual(
            report.chain,
            ["tests/test_report.py", "shop.report", "shop.pricing"],
        )
        pricing = next(s for s in selection.selected if s.path == "tests/test_pricing.py")
        self.assertEqual(
            pricing.chain,
            ["tests/test_pricing.py", "shop.pricing"],
        )

    def test_unrelated_tests_not_selected(self):
        selection = sample_selection("src/shop/pricing.py")
        self.assertNotIn("tests/test_inventory.py", selection.paths)
        self.assertNotIn("tests/test_utils.py", selection.paths)

    def test_direct_reason_wins_over_import(self):
        selection = sample_selection("tests/test_pricing.py", "src/shop/pricing.py")
        by_path = {s.path: s for s in selection.selected}
        self.assertEqual(by_path["tests/test_pricing.py"].reason, REASON_DIRECT)
        self.assertEqual(by_path["tests/test_report.py"].reason, REASON_IMPORT)

    def test_mixed_changed_test_and_source(self):
        selection = sample_selection("tests/test_inventory.py", "src/shop/pricing.py")
        by_path = {s.path: s for s in selection.selected}
        self.assertEqual(
            sorted(by_path),
            ["tests/test_inventory.py", "tests/test_pricing.py", "tests/test_report.py"],
        )
        self.assertEqual(by_path["tests/test_inventory.py"].reason, REASON_DIRECT)

    def test_changed_non_python_file_selects_nothing(self):
        selection = sample_selection("README.md")
        self.assertEqual(selection.paths, [])
        self.assertTrue(any("not a Python file" in n for n in selection.notes))
        self.assertIn("no tests selected", selection.notes)

    def test_fallback_name_match(self):
        selection = sample_selection("src/shop/utils.py")
        self.assertEqual(selection.paths, ["tests/test_utils.py"])
        item = selection.selected[0]
        self.assertEqual(item.reason, REASON_FALLBACK)
        self.assertTrue(item.fallback)
        self.assertIsNone(item.chain)

    def test_fallback_disabled(self):
        selection = sample_selection("src/shop/utils.py", use_fallback=False)
        self.assertEqual(selection.paths, [])
        self.assertIn("no tests selected", selection.notes)

    def test_fallback_not_used_when_imports_match(self):
        selection = sample_selection("src/shop/pricing.py")
        self.assertFalse(any(s.fallback for s in selection.selected))

    def test_module_without_tests_is_empty(self):
        selection = sample_selection("src/shop/shipping.py", use_fallback=False)
        self.assertEqual(selection.paths, [])

    def test_all_if_empty_selects_whole_suite(self):
        selection = sample_selection("src/shop/shipping.py", all_if_empty=True)
        self.assertEqual(
            selection.paths,
            [
                "tests/test_inventory.py",
                "tests/test_pricing.py",
                "tests/test_report.py",
                "tests/test_utils.py",
            ],
        )
        self.assertTrue(all(s.reason == REASON_ALL for s in selection.selected))

    def test_all_if_empty_skipped_when_matches_exist(self):
        selection = sample_selection("src/shop/pricing.py", all_if_empty=True)
        self.assertEqual(
            selection.paths, ["tests/test_pricing.py", "tests/test_report.py"]
        )

    def test_unindexed_python_file_is_noted(self):
        selection = sample_selection("does/not/exist.py")
        self.assertEqual(selection.paths, [])
        self.assertTrue(any("not found in index" in n for n in selection.notes))

    def test_backslash_paths_are_normalized(self):
        selection = sample_selection("src\\shop\\pricing.py")
        self.assertEqual(selection.changed, ["src/shop/pricing.py"])
        self.assertEqual(
            selection.paths, ["tests/test_pricing.py", "tests/test_report.py"]
        )

    def test_selected_output_is_sorted(self):
        selection = sample_selection(
            "tests/test_report.py", "src/shop/inventory.py", "src/shop/pricing.py"
        )
        self.assertEqual(selection.paths, sorted(selection.paths))


class NormalizePathTests(unittest.TestCase):
    def test_normalizes_separators_and_prefixes(self):
        self.assertEqual(normalize_path("src\\shop\\pricing.py"), "src/shop/pricing.py")
        self.assertEqual(normalize_path("./pkg/mod.py"), "pkg/mod.py")
        self.assertEqual(normalize_path("/pkg/mod.py"), "pkg/mod.py")
        self.assertEqual(normalize_path("  pkg/mod.py  "), "pkg/mod.py")


class SyntheticSelectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_flat_repo_selection(self):
        write_repo(
            self.root,
            {
                "pkg/__init__.py": "",
                "pkg/mod.py": "value = 1\n",
                "pkg/other.py": "import pkg.mod\n",
                "test_mod.py": "from pkg.mod import value\n",
                "test_other.py": "from pkg.other import x\n",
                "test_plain.py": "assert True\n",
            },
        )
        index = build_index(self.root, layout="flat")
        graph = build_graph(index)
        selection = select(index, graph, ["pkg/mod.py"])
        self.assertEqual(selection.paths, ["test_mod.py", "test_other.py"])

    def test_directly_changed_test_also_in_closure_case(self):
        write_repo(
            self.root,
            {
                "mod.py": "value = 1\n",
                "test_mod.py": "import mod\n",
            },
        )
        index = build_index(self.root, layout="flat")
        graph = build_graph(index)
        selection = select(index, graph, ["test_mod.py"])
        self.assertEqual(selection.paths, ["test_mod.py"])
        self.assertEqual(selection.selected[0].reason, REASON_DIRECT)


if __name__ == "__main__":
    unittest.main()
