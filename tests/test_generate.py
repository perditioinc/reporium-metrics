"""Tests for reporium-metrics generate.py."""

from __future__ import annotations

import json

from generate import _ascii_chart, _current_stats, build_readme, load_metrics

# ── load_metrics ──────────────────────────────────────────────────────────────


def test_load_metrics_returns_sorted(tmp_path):
    """Entries are sorted by date ascending."""
    entries = [
        {"date": "2026-03-17", "forksync_v1": None},
        {"date": "2026-02-01", "forksync_v1": None},
    ]
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(entries))
    loaded = load_metrics(path)
    assert loaded[0]["date"] == "2026-02-01"
    assert loaded[1]["date"] == "2026-03-17"


def test_load_metrics_missing_file(tmp_path):
    """Returns empty list for missing file."""
    assert load_metrics(tmp_path / "nope.json") == []


# ── _ascii_chart ──────────────────────────────────────────────────────────────


def test_ascii_chart_no_data():
    """Returns 'No data yet' when all values are None."""
    result = _ascii_chart([None, None], ["2026-03-01", "2026-03-02"], "Test")
    assert "No data" in result


def test_ascii_chart_single_entry():
    """Renders without crash for a single data point."""
    result = _ascii_chart([818.0], ["2026-03-17"], "Repos")
    assert "Repos" in result
    assert "```" in result


def test_ascii_chart_30_entries(thirty_entries):
    """Renders without crash for 30 entries."""
    values = [float(e["reporium_db"]["repos_tracked"]) for e in thirty_entries]
    labels = [e["date"] for e in thirty_entries]
    result = _ascii_chart(values, labels, "Repos Over Time")
    assert "Repos Over Time" in result
    assert "█" in result


def test_ascii_chart_format_has_code_block(thirty_entries):
    """Chart is wrapped in a markdown code block."""
    values = [float(e["reporium_db"]["repos_tracked"]) for e in thirty_entries]
    labels = [e["date"] for e in thirty_entries]
    result = _ascii_chart(values, labels, "Title")
    assert result.count("```") == 2


# ── _current_stats ────────────────────────────────────────────────────────────


def test_current_stats_shows_latest(one_entry):
    """Shows repos_tracked and forksync duration from most recent entry."""
    result = _current_stats(one_entry)
    assert "818" in result
    assert "68" in result


def test_current_stats_shows_zero_categories(one_entry):
    """Shows 0 for categories_enriched — not fabricated numbers."""
    result = _current_stats(one_entry)
    assert "0" in result


def test_current_stats_empty():
    """Returns '_No data yet._' for empty entries."""
    result = _current_stats([])
    assert "No data" in result


# ── build_readme ──────────────────────────────────────────────────────────────


def test_build_readme_one_entry(one_entry):
    """README renders correctly with one entry."""
    readme = build_readme(one_entry)
    assert "# Reporium Metrics" in readme
    assert "818" in readme
    assert "68" in readme


def test_build_readme_thirty_entries(thirty_entries):
    """README renders without crash for 30 entries."""
    readme = build_readme(thirty_entries)
    assert "# Reporium Metrics" in readme
    assert "Trends" in readme


def test_build_readme_sections(one_entry):
    """README has required sections."""
    readme = build_readme(one_entry)
    assert "## Current Stats" in readme
    assert "## Trends" in readme
    assert "## Status" in readme


def test_build_readme_shows_not_working(one_entry):
    """README honestly shows what is not working."""
    readme = build_readme(one_entry)
    assert "Not Working" in readme
    assert "ingestion" in readme.lower()


def test_build_readme_empty_entries():
    """README renders without crash when no entries exist."""
    readme = build_readme([])
    assert "# Reporium Metrics" in readme
