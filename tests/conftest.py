"""Shared fixtures for reporium-metrics tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def one_entry() -> list[dict]:
    """A single metrics entry."""
    return [
        {
            "date": "2026-03-17",
            "forksync": {
                "duration_seconds": 68,
                "repos_checked": 805,
                "peak_concurrency": 50,
                "api_calls": 856,
            },
            "reporium": {"repos_tracked": 805, "repos_enriched": 702, "categories": 12},
            "milestone": "forksync v2 launched",
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
                "forksync": {
                    "duration_seconds": 60 + i,
                    "repos_checked": 800 + i * 10,
                    "peak_concurrency": 50,
                    "api_calls": 850 + i,
                },
                "reporium": {
                    "repos_tracked": 800 + i * 10,
                    "categories": 12,
                },
            }
        )
    return entries
