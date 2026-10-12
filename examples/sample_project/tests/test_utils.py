"""Unrelated test: imports nothing from the shop package.

Used to show that tests without an import edge to the changed files are not
selected (and that the name-similarity fallback can pair it with
src/shop/utils.py by name only).
"""

import unittest


def initials(name):
    return "".join(part[0].upper() for part in name.split() if part)


class UtilsTests(unittest.TestCase):
    def test_initials(self):
        self.assertEqual(initials("ada lovelace"), "AL")

    def test_initials_empty(self):
        self.assertEqual(initials("  "), "")


if __name__ == "__main__":
    unittest.main()
