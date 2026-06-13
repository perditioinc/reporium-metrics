"""Tests guarding against mojibake / non-ASCII corruption in generated output.

The README and the metric source modules were corrupted by a CP1252 double-encode
(UTF-8 em-dash and middot read as Latin-1 then re-saved as UTF-8), leaving sequences
like ``a-EUR-"`` in committed files. These tests pin the output to ASCII so the
corruption cannot regress.
"""

from __future__ import annotations

from pathlib import Path

from generate import _ascii_chart, _current_stats, build_readme

REPO_ROOT = Path(__file__).resolve().parent.parent

# Byte signatures of the specific CP1252 double-encode corruption we are fixing.
EM_DASH_MOJIBAKE = "â€”"  # garbled em-dash ("a-EUR-quote")
MIDDOT_MOJIBAKE = "Â·"  # garbled middot


def _non_ascii(text: str) -> list[str]:
    """Return the distinct non-ASCII characters in ``text`` excluding the chart glyph."""
    # The ASCII bar chart legitimately uses U+2588 (full block) for bars; everything
    # else in the README is expected to be plain ASCII.
    return sorted({c for c in text if ord(c) > 127 and c != "█"})


# -- generated README is ASCII-clean --------------------------------------------


def test_build_readme_empty_is_ascii_only():
    """An empty-data README must not contain any mojibake or stray non-ASCII."""
    readme = build_readme([])
    leftovers = _non_ascii(readme)
    assert leftovers == [], f"unexpected non-ASCII chars: {leftovers!r}"


def test_build_readme_one_entry_is_ascii_only(one_entry):
    """A populated README must not contain any mojibake or stray non-ASCII."""
    readme = build_readme(one_entry)
    leftovers = _non_ascii(readme)
    assert leftovers == [], f"unexpected non-ASCII chars: {leftovers!r}"


def test_build_readme_thirty_entries_is_ascii_only(thirty_entries):
    """A 30-entry README (with a real chart) is ASCII apart from the bar glyph."""
    readme = build_readme(thirty_entries)
    leftovers = _non_ascii(readme)
    assert leftovers == [], f"unexpected non-ASCII chars: {leftovers!r}"


def test_build_readme_has_no_known_mojibake_signatures(one_entry):
    """The exact corruption signatures must be gone from the rendered README."""
    readme = build_readme(one_entry)
    assert EM_DASH_MOJIBAKE not in readme
    assert MIDDOT_MOJIBAKE not in readme


# -- no-data placeholders use an ASCII dash -------------------------------------


def test_current_stats_missing_values_use_ascii_dash(one_entry):
    """Absent metric values render as an ASCII '--' placeholder, never mojibake."""
    # one_entry has no reporium_db.languages-style API values for several rows.
    stats = _current_stats(one_entry)
    assert EM_DASH_MOJIBAKE not in stats
    # The forksync repos-synced row is absent in one_entry's v1 dict, so a dash shows.
    assert "--" in stats


def test_ascii_chart_no_data_is_ascii():
    """The 'No data yet' branch is ASCII-only."""
    out = _ascii_chart([None, None], ["2026-03-01", "2026-03-02"], "Test")
    assert _non_ascii(out) == []
    assert "No data" in out


# -- committed source files are ASCII -------------------------------------------


def test_generate_module_source_is_ascii():
    """generate.py must contain no mojibake-producing non-ASCII literals."""
    text = (REPO_ROOT / "generate.py").read_text(encoding="utf-8")
    leftovers = sorted({c for c in text if ord(c) > 127 and c != "█"})
    assert leftovers == [], f"non-ASCII in generate.py: {leftovers!r}"


def test_collect_module_source_is_ascii_apart_from_intended_glyphs():
    """collect.py parses emoji status markers; only those intended glyphs may remain."""
    text = (REPO_ROOT / "collect.py").read_text(encoding="utf-8")
    # No em-dash / middot mojibake signatures regardless of the emoji set.
    assert EM_DASH_MOJIBAKE not in text
    assert MIDDOT_MOJIBAKE not in text


def test_committed_readme_is_ascii_only():
    """The checked-in README.md must be free of mojibake after regeneration."""
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    leftovers = sorted({c for c in text if ord(c) > 127 and c != "█"})
    assert leftovers == [], f"non-ASCII in README.md: {leftovers!r}"
