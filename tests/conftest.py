"""Shared fixtures for reporium-metrics tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def one_entry() -> list[dict]:
    """A single metrics entry using the current schema."""
    return [
        {
            "date": "2026-03-17",
            "forksync_v1": {
                "duration_seconds": 891,
                "repos_checked": 494,
                "repos_synced": 201,
                "already_current": 265,
                "api_calls_used": 937,
                "source": "SYNC_REPORT.md",
            },
            "forksync_v2": {
                "duration_seconds": 68,
                "repos_checked": 818,
                "peak_concurrency": 50,
                "source": "Cloud Run logs",
            },
            "reporium_db": {
                "repos_tracked": 818,
                "languages": 29,
                "categories_enriched": 0,
                "source": "data/index.json",
            },
            "reporium_api": {
                "total_repos_in_db": 702,
                "repos_with_ai_dev_skills": 571,
                "repos_with_categories": 0,
                "repos_with_readme_summary": 0,
                "last_ingestion": None,
                "deployment": "local only",
                "source": "localhost:8000/stats",
            },
        }
    ]


@pytest.fixture
def thirty_entries() -> list[dict]:
    """30 days of metrics entries for chart testing."""
    entries = []
    for i in range(30):
        entries.append(
            {
                "date": f"2026-02-{i + 1:02d}",
                "forksync_v1": {
                    "duration_seconds": 891,
                    "repos_checked": 494,
                    "repos_synced": 200 + i,
                    "api_calls_used": 937,
                },
                "forksync_v2": {
                    "duration_seconds": 60 + i,
                    "repos_checked": 800 + i * 10,
                    "peak_concurrency": 50,
                },
                "reporium_db": {
                    "repos_tracked": 800 + i * 10,
                    "languages": 29,
                    "categories_enriched": 0,
                },
                "reporium_api": None,
            }
        )
    return entries
