"""Generate README.md with ASCII trend charts from metrics.json."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

METRICS_FILE = Path("metrics.json")
CHART_WIDTH = 40
CHART_HEIGHT = 8


def load_metrics(path: Path = METRICS_FILE) -> list[dict]:
    """Load metrics.json from disk."""
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        return sorted(entries, key=lambda e: e.get("date", ""))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load %s: %s", path, exc)
        return []


def _ascii_chart(values: list[Optional[float]], labels: list[str], title: str) -> str:
    """Render a simple ASCII bar chart."""
    valid = [v for v in values if v is not None]
    if not valid:
        return f"### {title}\n\n_No data yet._\n"

    if len(valid) == 1:
        first_label = labels[next(i for i, v in enumerate(values) if v is not None)]
        return (
            f"### {title}\n\n"
            "_Trend data will appear here after multiple nightly runs. "
            f"First data point: {int(valid[0]):,} repos on {first_label}._\n"
        )

    max_val = max(valid)
    min_val = min(valid)
    span = max_val - min_val or 1

    lines = [f"### {title}", "```"]
    for row in range(CHART_HEIGHT, 0, -1):
        threshold = min_val + span * (row / CHART_HEIGHT)
        bars = ""
        for value in values:
            if value is None:
                bars += " "
            elif value >= threshold:
                bars += "█"
            else:
                bars += " "
        y_label = f"{threshold:>7.0f} |" if row % 2 == 0 else "        |"
        lines.append(f"{y_label}{bars}")

    lines.append("        +" + "-" * len(values))

    step = max(1, len(labels) // 6)
    x_line = "         "
    for i, label in enumerate(labels):
        if i % step == 0:
            x_line += label[-5:]
            x_line += " "
    lines.append(x_line.rstrip())
    lines.append("```")
    return "\n".join(lines)


def _current_stats(entries: list[dict]) -> str:
    """Format the most recent entry as a stats table."""
    if not entries:
        return "_No data yet._"

    latest = entries[-1]
    fs1 = latest.get("forksync_v1") or {}
    fs2 = latest.get("forksync_v2") or {}
    db = latest.get("reporium_db") or {}
    api = latest.get("reporium_api") or {}
    backfill = latest.get("backfill_metrics") or {}
    graph_quality = latest.get("graph_quality") or {}
    api_latency = latest.get("api_latency") or {}

    def _fmt(value: object) -> str:
        if isinstance(value, int):
            return f"{value:,}"
        return str(value) if value is not None else "â€”"

    if fs2.get("duration_seconds") is not None:
        duration = f"{fs2['duration_seconds']}s (v2)"
        repos_checked = _fmt(fs2.get("repos_checked"))
    elif fs1.get("duration_seconds") is not None:
        duration = f"{fs1['duration_seconds']}s (v1)"
        repos_checked = _fmt(fs1.get("repos_checked"))
    else:
        duration = "no data"
        repos_checked = "â€”"

    rows = [
        f"| Date | {latest.get('date', 'â€”')} |",
        f"| Repos tracked (reporium-db) | {_fmt(db.get('repos_tracked'))} |",
        f"| Languages tracked | {_fmt(db.get('languages'))} |",
        f"| Categories enriched | {_fmt(db.get('categories_enriched'))} |",
        f"| Repos in API DB | {_fmt(api.get('repos_tracked'))} |",
        f"| Languages (API) | {_fmt(api.get('languages'))} |",
        f"| forksync sync duration | {duration} |",
        f"| forksync repos checked | {repos_checked} |",
        f"| forksync repos synced | {_fmt(fs1.get('repos_synced'))} |"
        if fs1 else "| forksync repos synced | â€” |",
    ]

    if backfill.get("available"):
        rows.append(
            f"| Dependency backfill coverage | {_fmt((backfill.get('repos') or {}).get('percent_complete'))}% |"
        )
    if graph_quality.get("available"):
        depends_on = ((graph_quality.get("edge_types") or {}).get("DEPENDS_ON") or {})
        rows.append(f"| DEPENDS_ON precision | {_fmt(depends_on.get('precision'))} |")
    if api_latency:
        graph_edges = (((api_latency.get("routes") or {}).get("/graph/edges") or {}).get("observed") or {})
        rows.append(f"| /graph/edges p95 | {_fmt(graph_edges.get('p95_ms'))} ms |")

    header = "| Metric | Value |\n|--------|-------|"
    return header + "\n" + "\n".join(rows)


def _status_section(entries: list[dict]) -> str:
    """Render a what-works / what-doesn't section from the latest entry."""
    if not entries:
        return ""

    latest = entries[-1]
    db = latest.get("reporium_db") or {}
    api = latest.get("reporium_api") or {}
    fs1 = latest.get("forksync_v1") or {}
    backfill = latest.get("backfill_metrics") or {}

    working = [
        "reporium.com â€” live, repos browseable",
        f"reporium-db â€” nightly sync active, {db.get('repos_tracked', 'â€”')} repos tracked, "
        f"{db.get('languages', 'â€”')} languages",
    ]

    if fs1.get("duration_seconds") is not None:
        working.append(
            f"forksync v2 â€” {fs1['duration_seconds']}s for {fs1.get('repos_checked', 'â€”')} repos"
            " on Cloud Run, SYNC_REPORT.md committed via GitHub API"
        )
    else:
        working.append("forksync v2 â€” running on Cloud Run (no SYNC_REPORT.md data available)")

    if api and api.get("repos_tracked") is not None:
        working.append(
            f"reporium-api â€” deployed to Cloud Run, {api.get('repos_tracked', 'â€”')} repos, "
            "Swagger UI public at /docs"
        )
    else:
        working.append("reporium-api â€” deployed to Cloud Run (metrics not yet collected)")

    if backfill.get("available"):
        working.append(
            "dependency observability â€” backfill coverage and ETA exposed at /metrics/backfill"
        )

    not_working = [
        "reporium-ingestion â€” pipeline not running, 0 categories enriched",
        "AI categories â€” requires ingestion pipeline to generate real categorization",
    ]

    working_md = "\n".join(f"- {item}" for item in working)
    broken_md = "\n".join(f"- {item}" for item in not_working)

    return f"""## Status

### Working
{working_md}

### Not Working
{broken_md}
"""


def _milestones_section() -> str:
    """Read and include MILESTONES.md content."""
    path = Path("MILESTONES.md")
    if path.exists():
        return "## Milestones\n\n" + path.read_text(encoding="utf-8")
    return ""


def build_readme(entries: list[dict]) -> str:
    """Build the full README.md from metrics entries."""
    dates = [e.get("date", "?") for e in entries]
    repos_tracked: list[Optional[float]] = [
        float(e.get("reporium_db", {}).get("repos_tracked", 0))
        if e.get("reporium_db") and e["reporium_db"].get("repos_tracked") is not None
        else None
        for e in entries
    ]

    repos_chart = _ascii_chart(repos_tracked, dates, "Repos Tracked Over Time")
    stats_table = _current_stats(entries)
    status = _status_section(entries)
    milestones = _milestones_section()

    decisions = """## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| GraphQL over REST | REST API required 826 individual calls. GraphQL batch does it in 9. |
| Cloud Run for forksync | GitHub Actions timeout at 6min could not support 13min v1 runtime. |
| Redis for caching | ETag caching reduces redundant compare API calls. |
| Neon over Cloud SQL | Cloud SQL costs $7-10/month minimum. Neon free tier supports pgvector. |
| Partitioned JSON | Single dataset.json would be 50MB+ at 100K repos. Partitioned files let frontend load only what it needs. |
| Pub/Sub events | Decouples services â€” forksync and reporium-db publish events, API and audit consume them. |
"""

    generated = entries[-1].get("date", "â€”") if entries else "â€”"

    return f"""# Reporium Metrics

<!-- perditio-badges-start -->
[![Tests](https://github.com/perditioinc/reporium-metrics/actions/workflows/test.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/test.yml)
[![Nightly](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-metrics)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Platform performance tracking. Verified numbers only â€” no estimates.

## Current Stats

{stats_table}

{status}
## Trends

{repos_chart}

{milestones}

{decisions}
---
*Last updated: {generated} Â· Data from live GitHub sources.*
"""


def main() -> None:
    """Load metrics and write README.md."""
    t0 = time.monotonic()
    entries = load_metrics()
    readme = build_readme(entries)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    elapsed = time.monotonic() - t0
    logger.info("README generated in %.2fs â€” %d entries", elapsed, len(entries))


if __name__ == "__main__":
    main()
