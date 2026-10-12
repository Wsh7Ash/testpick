"""Tests for ast import parsing, closure, cycles, and chain finding."""

import tempfile
import unittest
from pathlib import Path

from tests.helpers import write_repo

from testpick.graph import build_graph
from testpick.indexer import build_index


class ImportResolutionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _graph(self, files, layout="flat"):
        write_repo(self.root, files)
        index = build_index(self.root, layout=layout)
        return build_graph(index)

    def test_absolute_import(self):
        graph = self._graph(
            {
                "main.py": "import pkg.core\n",
                "pkg/__init__.py": "",
                "pkg/core.py": "value = 1\n",
            }
        )
        self.assertIn("pkg.core", graph.edges["main"])
        self.assertIn("pkg", graph.edges["main"])  # package prefix is executed too

    def test_absolute_from_import(self):
        graph = self._graph(
            {
                "main.py": "from pkg.core import helper\n",
                "pkg/__init__.py": "",
                "pkg/core.py": "def helper():\n    return 1\n",
            }
        )
        self.assertIn("pkg.core", graph.edges["main"])

    def test_import_outside_repo_ignored(self):
        graph = self._graph(
            {
                "main.py": "import requests\nfrom external.lib import thing\n",
                "pkg/__init__.py": "",
            }
        )
        self.assertEqual(graph.edges["main"], set())

    def test_relative_import_same_package(self):
        graph = self._graph(
            {
                "pkg/__init__.py": "",
                "pkg/mod.py": "from . import core\n",
                "pkg/core.py": "value = 1\n",
            }
        )
        self.assertIn("pkg.core", graph.edges["pkg.mod"])

    def test_relative_import_submodule_by_path(self):
        graph = self._graph(
            {
                "pkg/__init__.py": "",
                "pkg/mod.py": "from .core import value\n",
                "pkg/core.py": "value = 1\n",
            }
        )
        self.assertIn("pkg.core", graph.edges["pkg.mod"])

    def test_relative_import_parent_package(self):
        graph = self._graph(
            {
                "pkg/__init__.py": "",
                "pkg/core.py": "value = 1\n",
                "pkg/sub/__init__.py": "",
                "pkg/sub/deep.py": "from ..core import value\n",
            }
        )
        self.assertIn("pkg.core", graph.edges["pkg.sub.deep"])

    def test_relative_import_outside_root_skipped(self):
        graph = self._graph(
            {
                "top.py": "from . import helper\n",
                "helper.py": "value = 1\n",
            }
        )
        self.assertEqual(graph.edges["top"], set())

    def test_star_import_resolves_package_only(self):
        graph = self._graph(
            {
                "main.py": "from pkg.core import *\n",
                "pkg/__init__.py": "",
                "pkg/core.py": "value = 1\n",
            }
        )
        self.assertEqual(graph.edges["main"], {"pkg", "pkg.core"})

    def test_parse_error_is_recorded_not_fatal(self):
        graph = self._graph(
            {
                "broken.py": "def oops(:\n",
                "main.py": "import pkg\n",
                "pkg/__init__.py": "",
            }
        )
        self.assertEqual(graph.errors, ["broken.py"])
        self.assertIn("pkg", graph.edges["main"])


class ClosureAndChainTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _graph(self, files, layout="flat"):
        write_repo(self.root, files)
        index = build_index(self.root, layout=layout)
        return build_graph(index)

    def test_transitive_closure(self):
        graph = self._graph(
            {
                "main.py": "import mid\n",
                "mid.py": "import deep\n",
                "deep.py": "value = 1\n",
            }
        )
        self.assertEqual(graph.closure("main"), {"mid", "deep"})

    def test_closure_excludes_start_module(self):
        graph = self._graph({"main.py": "value = 1\n"})
        self.assertEqual(graph.closure("main"), set())

    def test_cycle_terminates(self):
        graph = self._graph(
            {
                "a.py": "import b\n",
                "b.py": "import a\n",
            }
        )
        self.assertEqual(graph.closure("a"), {"b"})
        self.assertEqual(graph.closure("b"), {"a"})

    def test_mutual_cycle_with_self_target(self):
        graph = self._graph(
            {
                "a.py": "import b\n",
                "b.py": "import a\n",
                "c.py": "import a\n",
            }
        )
        self.assertEqual(graph.closure("c"), {"a", "b"})

    def test_chain_transitive(self):
        graph = self._graph(
            {
                "main.py": "import mid\n",
                "mid.py": "import deep\n",
                "deep.py": "value = 1\n",
            }
        )
        self.assertEqual(graph.chain("main", "deep"), ["main", "mid", "deep"])

    def test_chain_direct(self):
        graph = self._graph({"main.py": "import dep\n", "dep.py": "x = 1\n"})
        self.assertEqual(graph.chain("main", "dep"), ["main", "dep"])

    def test_chain_none_when_unrelated(self):
        graph = self._graph({"main.py": "x = 1\n", "other.py": "y = 2\n"})
        self.assertIsNone(graph.chain("main", "other"))


if __name__ == "__main__":
    unittest.main()
