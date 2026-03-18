"""Tests for reporium-metrics collect.py."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import respx

from collect import collect, load_metrics, parse_index_json, parse_sync_report, save_metrics

GITHUB_RAW = "https://raw.githubusercontent.com"
FORKSYNC_REPO = "perditioinc/forksync"
DB_REPO = "perditioinc/reporium-db"

SAMPLE_SYNC_REPORT = """
# Sync Report
- Duration: 68s
- Repos checked: 805
- Peak concurrency: 50
- API calls: 856
- Repos synced: 10
- Errors: 0
"""

SAMPLE_INDEX = {
    "meta": {"total": 805, "last_updated": "2026-03-17T05:00:00+00:00", "version": "1.0.0"},
    "categories": {"llm": 300, "rag": 100},
    "languages": {"Python": 400},
}


# ── parse_sync_report ─────────────────────────────────────────────────────────


def test_parse_sync_report_extracts_all_fields():
    """Parses all expected fields from SYNC_REPORT.md."""
    result = parse_sync_report(SAMPLE_SYNC_REPORT)
    assert result["duration_seconds"] == 68
    assert result["repos_checked"] == 805
    assert result["peak_concurrency"] == 50
    assert result["api_calls"] == 856
    assert result["repos_synced"] == 10
    assert result["errors"] == 0


def test_parse_sync_report_missing_fields():
    """Returns empty dict for empty or irrelevant text."""
    result = parse_sync_report("nothing relevant here")
    assert result == {}


def test_parse_sync_report_partial():
    """Only returns fields that are present."""
    text = "- Duration: 42s\n- Repos checked: 100"
    result = parse_sync_report(text)
    assert result["duration_seconds"] == 42
    assert result["repos_checked"] == 100
    assert "api_calls" not in result


# ── parse_index_json ──────────────────────────────────────────────────────────


def test_parse_index_json():
    """Extracts total, category count, and last_updated."""
    result = parse_index_json(SAMPLE_INDEX)
    assert result["repos_tracked"] == 805
    assert result["categories"] == 2
    assert result["last_updated"] == "2026-03-17T05:00:00+00:00"


# ── load_metrics / save_metrics ───────────────────────────────────────────────


def test_load_metrics_missing_file(tmp_path):
    """Returns empty list when metrics.json doesn't exist."""
    result = load_metrics(tmp_path / "metrics.json")
    assert result == []


def test_save_and_load_metrics(tmp_path):
    """Round-trips metrics through save/load."""
    path = tmp_path / "metrics.json"
    entries = [{"date": "2026-03-17", "forksync": {"duration_seconds": 68}}]

    with patch("collect.METRICS_FILE", path):
        save_metrics(entries)
        loaded = load_metrics(path)

    assert len(loaded) == 1
    assert loaded[0]["date"] == "2026-03-17"


def test_save_metrics_atomic(tmp_path):
    """No .tmp file remains after save."""
    path = tmp_path / "metrics.json"
    with patch("collect.METRICS_FILE", path):
        save_metrics([{"date": "2026-03-17"}])
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
    assert loaded[0]["forksync"]["duration_seconds"] == 68


@respx.mock
async def test_collect_skips_duplicate(tmp_path):
    """Returns None and does not append when today's entry already exists."""
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = [{"date": today, "forksync": None, "reporium": None}]
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps(existing))

    with patch("collect.METRICS_FILE", metrics_path):
        entry = await collect("test-token")

    assert entry is None
    loaded = json.loads(metrics_path.read_text())
    assert len(loaded) == 1  # no new entry added


@respx.mock
async def test_collect_uses_null_when_forksync_unavailable(tmp_path):
    """Uses null for forksync fields when SYNC_REPORT.md is unavailable."""
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text("[]")

    forksync_url = f"{GITHUB_RAW}/{FORKSYNC_REPO}/main/SYNC_REPORT.md"
    db_url = f"{GITHUB_RAW}/{DB_REPO}/main/data/index.json"
    respx.get(forksync_url).mock(return_value=httpx.Response(404))
    respx.get(db_url).mock(return_value=httpx.Response(200, json=SAMPLE_INDEX))

    with patch("collect.METRICS_FILE", metrics_path):
        entry = await collect("test-token")

    assert entry is not None
    assert entry["forksync"] is None
    assert entry["reporium"] is not None
