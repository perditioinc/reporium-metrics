"""No-data rendering and 'verified numbers only' fidelity tests.

These pin two promises the README makes:

1. generate.py must render an honest README when there is no data (no crash,
   no fabricated numbers, explicit "no data" placeholders).
2. collect.py must only record verified counts -- placeholder categories
   ("tooling"/"unknown") never inflate categories_enriched, and unavailable
   upstream sources are recorded as null rather than guessed.
"""

from __future__ import annotations

from collect import parse_index_json
from generate import _ascii_chart, _current_stats, _status_section, build_readme

# -- generate.py: empty / no-data rendering --------------------------------------


def test_build_readme_empty_does_not_crash_and_is_honest():
    """Empty entries render a full README with explicit no-data markers."""
    readme = build_readme([])
    # Required structural sections still present.
    assert "# Reporium Metrics" in readme
    assert "## Current Stats" in readme
    assert "## Trends" in readme
    # Honest placeholders, not invented values.
    assert "_No data yet._" in readme
    # No fabricated date in the footer.
    assert "*Last updated: n/a" in readme


def test_current_stats_empty_is_no_data_only():
    """_current_stats([]) returns exactly the no-data sentinel, no fake rows."""
    result = _current_stats([])
    assert result == "_No data yet._"
    assert "|" not in result  # no fabricated table rows


def test_status_section_empty_is_blank():
    """_status_section([]) emits nothing (cannot claim what 'works' with no data)."""
    assert _status_section([]) == ""


def test_ascii_chart_all_none_is_no_data():
    """A chart over all-None values shows 'No data', never a zero-height bar."""
    result = _ascii_chart([None, None, None], ["a", "b", "c"], "Repos")
    assert "_No data yet._" in result
    assert "```" not in result  # no empty code-block chart rendered


def test_ascii_chart_single_point_is_not_a_fake_trend():
    """One data point is described, not drawn as a misleading trend chart."""
    result = _ascii_chart([818.0], ["2026-03-17"], "Repos")
    assert "818" in result
    assert "multiple nightly runs" in result
    assert "```" not in result


def test_build_readme_none_db_entry_does_not_fabricate_repos():
    """An entry whose reporium_db is None must not invent a repos_tracked number."""
    entries = [{"date": "2026-04-01", "forksync_v1": None, "reporium_db": None}]
    readme = build_readme(entries)
    assert "2026-04-01" in readme
    # Missing db metrics render as the '--' placeholder, never a guessed count.
    assert "| Repos tracked (reporium-db) | -- |" in readme


# -- collect.py: 'verified numbers only' aggregation -----------------------------


def test_categories_enriched_excludes_placeholder_buckets():
    """tooling/unknown are placeholders -- they never count as enrichment."""
    data = {
        "meta": {"total": 1000},
        "categories": {"tooling": 600, "unknown": 400},
        "languages": {"Python": 500},
    }
    result = parse_index_json(data)
    assert result["categories_enriched"] == 0
    assert result["repos_tracked"] == 1000


def test_categories_enriched_counts_only_real_buckets():
    """Only genuine category buckets contribute to categories_enriched."""
    data = {
        "meta": {"total": 1000},
        "categories": {"llm": 300, "rag": 200, "tooling": 400, "unknown": 100},
        "languages": {"Python": 500, "TypeScript": 100},
    }
    result = parse_index_json(data)
    assert result["categories_enriched"] == 2  # llm + rag only
    assert result["languages"] == 2


def test_parse_index_missing_total_is_none_not_zero():
    """A missing repos total is recorded as None, never silently coerced to 0."""
    data = {"meta": {}, "categories": {"llm": 5}, "languages": {"Python": 5}}
    result = parse_index_json(data)
    assert result["repos_tracked"] is None


def test_parse_index_empty_categories_is_zero_enriched():
    """No categories at all means zero enrichment, not a fabricated count."""
    data = {"meta": {"total": 10}, "categories": {}, "languages": {"Go": 10}}
    result = parse_index_json(data)
    assert result["categories_enriched"] == 0
