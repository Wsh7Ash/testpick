"""Tests for list, cmd, json, and explain output shapes."""

import json
import unittest

from tests.helpers import SAMPLE

from testpick.graph import build_graph
from testpick.indexer import build_index
from testpick.report import (
    build_command,
    dotted_path,
    render_cmd,
    render_explain,
    render_json,
    render_list,
)
from testpick.select import select


def make_selection(*changed, **kwargs):
    index = build_index(SAMPLE, layout="auto")
    graph = build_graph(index)
    return select(index, graph, list(changed), **kwargs), index


class ListAndCmdTests(unittest.TestCase):
    def test_list_is_sorted_one_path_per_line(self):
        selection, index = make_selection("src/shop/pricing.py")
        output = render_list(selection)
        self.assertEqual(output.splitlines(), ["tests/test_pricing.py", "tests/test_report.py"])
        self.assertEqual(output.splitlines(), sorted(output.splitlines()))

    def test_list_empty_selection(self):
        selection, index = make_selection("README.md")
        self.assertEqual(render_list(selection), "")

    def test_cmd_unittest_uses_dotted_paths(self):
        selection, index = make_selection("src/shop/pricing.py")
        output = render_cmd(selection, "unittest", index)
        self.assertEqual(
            output, "python -m unittest tests.test_pricing tests.test_report"
        )

    def test_cmd_pytest_uses_file_paths(self):
        selection, index = make_selection("src/shop/pricing.py")
        output = render_cmd(selection, "pytest", index)
        self.assertEqual(
            output, "python -m pytest tests/test_pricing.py tests/test_report.py"
        )

    def test_cmd_empty_when_nothing_selected(self):
        selection, index = make_selection("README.md")
        self.assertEqual(render_cmd(selection, "unittest", index), "")
        self.assertIsNone(build_command(selection, "unittest", index))

    def test_dotted_path_helper(self):
        self.assertEqual(dotted_path("tests/test_a.py"), "tests.test_a")
        self.assertEqual(dotted_path("test_a.py"), "test_a")


class JsonTests(unittest.TestCase):
    def test_json_top_level_shape(self):
        selection, index = make_selection("src/shop/pricing.py")
        payload = json.loads(render_json(selection, "unittest", index))
        self.assertEqual(
            list(payload), ["changed", "selected", "format", "runner", "command"]
        )
        self.assertEqual(payload["changed"], ["src/shop/pricing.py"])
        self.assertEqual(payload["format"], "json")
        self.assertEqual(payload["runner"], "unittest")
        self.assertEqual(
            payload["command"], "python -m unittest tests.test_pricing tests.test_report"
        )

    def test_json_import_item_has_chain(self):
        selection, index = make_selection("src/shop/pricing.py")
        payload = json.loads(render_json(selection, "unittest", index))
        report = next(i for i in payload["selected"] if i["path"] == "tests/test_report.py")
        self.assertEqual(list(report), ["path", "reason", "chain", "fallback"])
        self.assertEqual(report["reason"], "import-chain")
        self.assertEqual(
            report["chain"],
            ["tests/test_report.py", "shop.report", "shop.pricing"],
        )
        self.assertIs(report["fallback"], False)

    def test_json_direct_item_has_no_chain(self):
        selection, index = make_selection("tests/test_inventory.py")
        payload = json.loads(render_json(selection, "unittest", index))
        item = payload["selected"][0]
        self.assertEqual(item["reason"], "direct")
        self.assertNotIn("chain", item)
        self.assertIs(item["fallback"], False)

    def test_json_fallback_item_flagged(self):
        selection, index = make_selection("src/shop/utils.py")
        payload = json.loads(render_json(selection, "unittest", index))
        item = payload["selected"][0]
        self.assertEqual(item["reason"], "fallback-name-match")
        self.assertIs(item["fallback"], True)
        self.assertNotIn("chain", item)

    def test_json_empty_selection(self):
        selection, index = make_selection("README.md")
        payload = json.loads(render_json(selection, "unittest", index))
        self.assertEqual(payload["selected"], [])
        self.assertIsNone(payload["command"])

    def test_json_deterministic(self):
        first, index = make_selection("src/shop/pricing.py")
        second, _ = make_selection("src/shop/pricing.py")
        self.assertEqual(
            render_json(first, "unittest", index), render_json(second, "unittest", index)
        )


class ExplainTests(unittest.TestCase):
    def test_explain_shows_transitive_chain_with_changed_marker(self):
        selection, index = make_selection("src/shop/pricing.py")
        output = render_explain(selection)
        self.assertIn(
            "chain: tests/test_report.py -> shop.report -> shop.pricing (changed)",
            output,
        )
        self.assertIn(
            "chain: tests/test_pricing.py -> shop.pricing (changed)", output
        )
        self.assertIn("changed: src/shop/pricing.py", output)
        self.assertIn("selected 2 test file(s):", output)

    def test_explain_direct_reason(self):
        selection, index = make_selection("tests/test_inventory.py")
        output = render_explain(selection)
        self.assertIn("reason: direct", output)
        self.assertIn("tests/test_inventory.py", output)

    def test_explain_fallback_reason(self):
        selection, index = make_selection("src/shop/utils.py")
        output = render_explain(selection)
        self.assertIn("reason: fallback-name-match", output)
        self.assertIn("selected by name similarity", output)

    def test_explain_all_if_empty_reason(self):
        selection, index = make_selection("src/shop/shipping.py", all_if_empty=True)
        output = render_explain(selection)
        self.assertIn("reason: all_if_empty", output)
        self.assertIn("selected 4 test file(s):", output)

    def test_explain_zero_selections(self):
        selection, index = make_selection("README.md")
        output = render_explain(selection)
        self.assertIn("selected 0 test file(s):", output)


if __name__ == "__main__":
    unittest.main()
