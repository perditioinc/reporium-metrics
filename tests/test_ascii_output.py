"""Regression tests for ASCII-only output (CP1252 em-dash mojibake guard).

The README and the metric `source` strings were corrupted at some point by a
CP1252 round-trip: a real em-dash (U+2014) became the three-byte sequence
E2 80 94, which decodes under UTF-8 to U+00E2 U+20AC U+201D and renders as
mojibake. These tests pin generate.py's output and collect.py's literal strings
to printable ASCII so the corruption cannot return.
"""

from __future__ import annotations

import inspect

import collect
from generate import build_readme

# The exact mojibake string, built from code points so this file stays ASCII.
# CP1252 mis-decode of U+2014 -> bytes E2 80 94 -> UTF-8 U+00E2 U+20AC U+201D.
MOJIBAKE = "\u00e2\u20ac\u201d"

# Full block glyph (U+2588) used intentionally in the ASCII bar chart body.
_CHART_BLOCK = "\u2588"


def _non_ascii(text: str) -> list[str]:
    """Distinct non-ASCII chars in ``text`` (excluding the chart block glyph)."""
    return sorted({ch for ch in text if ord(ch) > 127 and ch != _CHART_BLOCK})


def test_build_readme_empty_is_ascii():
    """README rendered from zero entries contains no mojibake / non-ASCII."""
    readme = build_readme([])
    assert MOJIBAKE not in readme
    assert _non_ascii(readme) == [], f"unexpected non-ASCII: {_non_ascii(readme)!r}"


def test_build_readme_one_entry_is_ascii(one_entry):
    """README rendered from a populated entry stays ASCII (chart block aside)."""
    readme = build_readme(one_entry)
    assert MOJIBAKE not in readme
    assert _non_ascii(readme) == [], f"unexpected non-ASCII: {_non_ascii(readme)!r}"


def test_collect_source_strings_are_ascii():
    """The literal `source`/log strings in collect.py are mojibake-free."""
    src = inspect.getsource(collect)
    assert MOJIBAKE not in src, "collect.py still contains CP1252 em-dash mojibake"


def test_generate_source_strings_are_ascii():
    """The literal strings in generate.py are mojibake-free."""
    import generate

    src = inspect.getsource(generate)
    assert MOJIBAKE not in src, "generate.py still contains CP1252 em-dash mojibake"


def test_parse_index_source_label_is_ascii():
    """parse_index_json stamps an ASCII `source` label, not mojibake."""
    result = collect.parse_index_json(
        {"meta": {"total": 5}, "categories": {"llm": 5}, "languages": {"Python": 5}}
    )
    assert MOJIBAKE not in result["source"]
    assert _non_ascii(result["source"]) == []
