"""Tests enforcing the 'verified numbers only -- no estimates' contract.

collect.py aggregates upstream reports (SYNC_REPORT.md, reporium-db index.json) into
the metrics record that generate.py renders. The README promises verified numbers and
explicitly no fabricated/estimated values. These tests pin that behaviour:

* missing upstream fields must be *absent*, never coerced to 0 or a guess
* category enrichment must exclude the placeholder 'tooling'/'unknown' buckets
* generate.py must surface absent values as a dash, not invent a number
"""

from __future__ import annotations

from collect import parse_index_json, parse_sync_report
from generate import _current_stats

# -- parse_sync_report: no fabrication ------------------------------------------


def test_sync_report_absent_fields_are_omitted_not_zeroed():
    """Fields missing from the report must not appear (not silently set to 0)."""
    text = "- duration_seconds: 42\n- repos_checked: 100"
    result = parse_sync_report(text)
    assert result == {"duration_seconds": 42, "repos_checked": 100}
    # The following were never reported and must be entirely absent.
    for fabricated in ("repos_synced", "already_current", "api_calls_used", "errors"):
        assert fabricated not in result


def test_sync_report_empty_input_yields_no_numbers():
    """A report with no machine-readable content yields an empty dict."""
    assert parse_sync_report("") == {}
    assert parse_sync_report("garbage with no fields") == {}


def test_sync_report_zero_is_preserved_not_dropped():
    """A genuine reported 0 (e.g. errors: 0) is a verified number and must survive."""
    text = "- duration_seconds: 10\n- errors: 0"
    result = parse_sync_report(text)
    assert result["errors"] == 0  # real reported zero, distinct from 'absent'


def test_sync_report_does_not_partial_count_without_evidence():
    """repos_checked is only derived when the table actually carries counts."""
    text = "# Fork Sync Report\nNo table, no fields here.\n"
    result = parse_sync_report(text)
    assert "repos_checked" not in result


# -- parse_index_json: enrichment counts real categories only -------------------


def test_index_enrichment_excludes_placeholder_buckets():
    """'tooling' and 'unknown' are not real enrichment and must not be counted."""
    data = {
        "meta": {"total": 500},
        "categories": {"tooling": 200, "unknown": 100, "llm": 50, "rag": 25},
        "languages": {"Python": 300, "Go": 50},
    }
    result = parse_index_json(data)
    assert result["categories_enriched"] == 2  # only llm + rag
    assert result["repos_tracked"] == 500
    assert result["languages"] == 2


def test_index_all_placeholder_categories_is_zero_enrichment():
    """If every category is a placeholder, enrichment is honestly 0."""
    data = {
        "meta": {"total": 818},
        "categories": {"tooling": 818, "unknown": 0},
        "languages": {"Python": 400},
    }
    result = parse_index_json(data)
    assert result["categories_enriched"] == 0


def test_index_missing_meta_total_is_none_not_zero():
    """Absent repo total must be None (unknown), not a fabricated 0."""
    data = {"meta": {}, "categories": {"llm": 5}, "languages": {"Python": 1}}
    result = parse_index_json(data)
    assert result["repos_tracked"] is None


# -- generate.py: absent values render as a dash, not a number ------------------


def test_current_stats_renders_dash_for_absent_api_values(one_entry):
    """When API metrics are absent, the stats table shows a dash -- never a guess."""
    # one_entry has reporium_api with no 'repos_tracked'/'languages' API fields here.
    entry = [dict(one_entry[0])]
    entry[0]["reporium_api"] = None  # API metrics not collected
    stats = _current_stats(entry)
    assert "Repos in API DB | -- |" in stats
    assert "Languages (API) | -- |" in stats


def test_current_stats_does_not_invent_forksync_when_absent():
    """With no forksync data at all, duration reads 'no data' rather than 0s."""
    entry = [
        {
            "date": "2026-04-01",
            "forksync_v1": None,
            "forksync_v2": None,
            "reporium_db": {"repos_tracked": 10, "languages": 3, "categories_enriched": 0},
            "reporium_api": None,
        }
    ]
    stats = _current_stats(entry)
    assert "no data" in stats
    assert "0s" not in stats  # never fabricate a zero-second sync
