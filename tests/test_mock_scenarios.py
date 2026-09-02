"""Guards on the demo fixture table itself.

A dict literal with a repeated key is legal Python: the last one silently wins.
That happened while adding the Act VIII landline scenario — a whole scenario was
dead on arrival and the only symptom was a demo showing the wrong evidence.
"""

from __future__ import annotations

import ast
from pathlib import Path

MOCK = Path("app/providers/mock.py")


def _scenario_keys() -> list[str]:
    """Read the keys from the SOURCE, not the dict.

    By the time the module is imported the duplicate is already gone — the
    collapse is what we are trying to detect, so it has to be caught before
    Python performs it.
    """
    tree = ast.parse(MOCK.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "SCENARIOS":
            return [
                key.value
                for key in node.value.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            ]
    raise AssertionError("SCENARIOS not found in app/providers/mock.py")


def test_no_scenario_number_is_defined_twice():
    keys = _scenario_keys()
    duplicates = {key for key in keys if keys.count(key) > 1}
    assert not duplicates, f"later definition silently wins for: {sorted(duplicates)}"


def test_every_scenario_number_is_e164():
    import re

    for key in _scenario_keys():
        assert re.fullmatch(r"\+[1-9]\d{7,14}", key), key
