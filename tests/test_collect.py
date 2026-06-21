"""Tests for reporium-metrics collect.py."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import httpx
import respx

from collect import collect, load_metrics, parse_index_json, parse_sync_report, save_metrics

GITHUB_RAW = "https://raw.githubusercontent.com"
FORKSYNC_REPO = "perditioinc/forksync"
DB_REPO = "perditioinc/reporium-db"

# Dynamic dates – never hardcode a calendar date in test fixtures
_NOW = datetime.now(timezone.utc)
_TODAY = _NOW.strftime("%Y-%m-%d")
_YESTERDAY = (_NOW - timedelta(days=1)).strftime("%Y-%m-%d")
_LAST_WEEK = (_NOW - timedelta(days=7)).strftime("%Y-%m-%d")
_TODAY_ISO = _NOW.strftime("%Y-%m-%dT%H:%M:%S+00:00")

# Field format (forksync v2 SYNC_REPORT.md written by workflow)
SAMPLE_SYNC_REPORT = f"""
# Fork Sync Report
**perditioinc's GitHub Forks** · {_TODAY} 12:00 UTC · 68s

## Machine-readable fields
- date: {_TODAY}
- duration_seconds: 68
- repos_checked: 818
- repos_synced: 201
- already_current: 265
- api_calls_used: 937
- errors: 0
- peak_concurrency: 50
"""

SAMPLE_INDEX = {
    "meta": {"total": 818, "last_updated": _TODAY_ISO, "version": "1.0.0"},
    "categories": {"llm": 300, "rag": 100},
    "languages": {"Python": 400, "TypeScript": 100},
}


# ── parse_sync_report ─────────────────────────────────────────────────────────


def test_parse_sync_report_extracts_all_fields():
    """Parses all expected fields from machine-readable SYNC_REPORT.md."""
    result = parse_sync_report(SAMPLE_SYNC_REPORT)
    assert result["duration_seconds"] == 68
    assert result["repos_checked"] == 818
    assert result["repos_synced"] == 201
    assert result["already_current"] == 265
    assert result["api_calls_used"] == 937
    assert result["errors"] == 0
    assert result["peak_concurrency"] == 50


def test_parse_sync_report_missing_fields():
    """Returns empty dict for empty or irrelevant text."""
    result = parse_sync_report("nothing relevant here")
    assert result == {}


def test_parse_sync_report_partial():
    """Only returns fields that are present."""
    text = "- duration_seconds: 42\n- repos_checked: 100"
    result = parse_sync_report(text)
    assert result["duration_seconds"] == 42
    assert result["repos_checked"] == 100
    assert "api_calls_used" not in result


def test_parse_sync_report_v1_table_format():
    """Parses v1 table format with duration from header."""
    text = f"""# Fork Sync Report
**perditioinc** · {_LAST_WEEK} · 14m 51s

| Status | Count |
|--------|-------|
| Synced | 201 |
| Already current | 265 |

**API calls used**: 937 / 5,000
"""
    result = parse_sync_report(text)
    assert result["duration_seconds"] == 891
    assert result["repos_synced"] == 201
    assert result["api_calls_used"] == 937


# ── parse_index_json ──────────────────────────────────────────────────────────


def test_parse_index_json():
    """Extracts repos_tracked, language count, and categories_enriched."""
    result = parse_index_json(SAMPLE_INDEX)
    assert result["repos_tracked"] == 818
    assert result["languages"] == 2
    assert result["categories_enriched"] == 2  # llm, rag are real categories
    assert result["last_updated"] == _TODAY_ISO


def test_parse_index_json_tooling_not_counted():
    """'tooling' and 'unknown' categories don't count as real enrichment."""
    data = {
        "meta": {"total": 818},
        "categories": {"tooling": 818},
        "languages": {"Python": 400},
    }
    result = parse_index_json(data)
    assert result["categories_enriched"] == 0


# ── load_metrics / save_metrics ───────────────────────────────────────────────


def test_load_metrics_missing_file(tmp_path):
    """Returns empty list when metrics.json doesn't exist."""
    result = load_metrics(tmp_path / "metrics.json")
    assert result == []


def test_save_and_load_metrics(tmp_path):
    """Round-trips metrics through save/load."""
    path = tmp_path / "metrics.json"
    entries = [{"date": _YESTERDAY, "forksync_v1": {"duration_seconds": 68}}]

    with patch("collect.METRICS_FILE", path):
        save_metrics(entries)
        loaded = load_metrics(path)

    assert len(loaded) == 1
    assert loaded[0]["date"] == _YESTERDAY


def test_save_metrics_atomic(tmp_path):
    """No .tmp file remains after save."""
    path = tmp_path / "metrics.json"
    with patch("collect.METRICS_FILE", path):
        save_metrics([{"date": _YESTERDAY}])
    assert not path.with_suffix(".tmp").exists()


# ── collect ───────────────────────────────────────────────────────────────────


@respx.mock
async def test_collect_appends_new_entry(tmp_path):
    """Appends a new entry to metrics.json when none exists for today."""
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text("[]")

    forksync_url = f"{GITHUB_RAW}/{FORKSYNC_REPO}/main/SYNC_REPORT.md"
    db_url = f"{GITHUB_RAW}/{DB_REPO}/main/data/index.json"
    respx.get(forksync_url).mock(return_value=httpx.Response(200, text=SAMPLE_SYNC_REPORT))
    respx.get(db_url).mock(return_value=httpx.Response(200, json=SAMPLE_INDEX))

    with patch("collect.METRICS_FILE", metrics_path):
        entry = await collect("test-token")

    assert entry is not None
    loaded = json.loads(metrics_path.read_text())
    assert len(loaded) == 1
    assert loaded[0]["forksync_v1"]["duration_seconds"] == 68
    assert loaded[0]["forksync_v2"] is None
    assert loaded[0]["reporium_api"] is None


@respx.mock
async def test_collect_skips_duplicate(tmp_path):
    """Returns None and does not append when today's entry already exists."""
    existing = [{"date": _TODAY, "forksync_v1": None, "reporium_db": None}]
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps(existing))

    with patch("collect.METRICS_FILE", metrics_path):
        entry = await collect("test-token")

    assert entry is None
    loaded = json.loads(metrics_path.read_text())
    assert len(loaded) == 1  # no new entry added


@respx.mock
async def test_collect_uses_null_when_forksync_unavailable(tmp_path):
    """Uses null for forksync_v1 when SYNC_REPORT.md is unavailable."""
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text("[]")

    forksync_url = f"{GITHUB_RAW}/{FORKSYNC_REPO}/main/SYNC_REPORT.md"
    db_url = f"{GITHUB_RAW}/{DB_REPO}/main/data/index.json"
    respx.get(forksync_url).mock(return_value=httpx.Response(404))
    respx.get(db_url).mock(return_value=httpx.Response(200, json=SAMPLE_INDEX))

    with patch("collect.METRICS_FILE", metrics_path):
        entry = await collect("test-token")

    assert entry is not None
    assert entry["forksync_v1"] is None
    assert entry["reporium_db"] is not None


@respx.mock
async def test_collect_fetches_api_observability_surfaces(tmp_path):
    """When REPORIUM_API_URL is configured, the collector stores the new metrics snapshots."""
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text("[]")

    forksync_url = f"{GITHUB_RAW}/{FORKSYNC_REPO}/main/SYNC_REPORT.md"
    db_url = f"{GITHUB_RAW}/{DB_REPO}/main/data/index.json"
    api_base = "https://api.example.com"

    respx.get(forksync_url).mock(return_value=httpx.Response(200, text=SAMPLE_SYNC_REPORT))
    respx.get(db_url).mock(return_value=httpx.Response(200, json=SAMPLE_INDEX))
    respx.get(f"{api_base}/metrics/latest").mock(
        return_value=httpx.Response(200, json={"repos_tracked": 1732, "languages": 40})
    )
    respx.get(f"{api_base}/metrics/backfill").mock(
        return_value=httpx.Response(
            200,
            json={"available": True, "repos": {"percent_complete": 64.2}},
        )
    )
    respx.get(f"{api_base}/metrics/graph-quality").mock(
        return_value=httpx.Response(
            200,
            json={"available": True, "edge_types": {"DEPENDS_ON": {"precision": 0.98}}},
        )
    )
    respx.get(f"{api_base}/metrics/latency").mock(
        return_value=httpx.Response(
            200,
            json={"routes": {"/graph/edges": {"observed": {"p95_ms": 180.0}}}},
        )
    )
    respx.get(f"{api_base}/graph/edges").mock(
        return_value=httpx.Response(200, json={"total": 99, "edgeTypes": []})
    )

    with (
        patch("collect.METRICS_FILE", metrics_path),
        patch("collect.REPORIUM_API_URL", api_base),
    ):
        entry = await collect("test-token")

    assert entry is not None
    assert entry["reporium_api"]["repos_tracked"] == 1732
    assert entry["backfill_metrics"]["repos"]["percent_complete"] == 64.2
    assert entry["graph_quality"]["edge_types"]["DEPENDS_ON"]["precision"] == 0.98
    assert entry["api_latency"]["routes"]["/graph/edges"]["observed"]["p95_ms"] == 180.0
