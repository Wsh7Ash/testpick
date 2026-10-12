"""Standalone helpers that no other shop module and no test imports.

Exists so name-similarity fallback can be demonstrated: changing this file
matches tests/test_utils.py by name only; there is no import edge.
"""


def initials(name):
    return "".join(part[0].upper() for part in name.split() if part)
