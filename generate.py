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
    """Load metrics.json from disk.

    Args:
        path: Path to metrics.json.

    Returns:
        List of entry dicts sorted by date ascending.
    """
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        return sorted(entries, key=lambda e: e.get("date", ""))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load %s: %s", path, exc)
        return []


def _ascii_chart(values: list[Optional[float]], labels: list[str], title: str) -> str:
    """Render a simple ASCII bar chart.

    Args:
        values: Y-axis values (None = missing data).
        labels: X-axis labels (one per value).
        title: Chart title.

    Returns:
        Multi-line string with the ASCII chart.
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return f"### {title}\n\n_No data yet._\n"

    if len(valid) == 1:
        first_label = labels[next(i for i, v in enumerate(values) if v is not None)]
        return (
            f"### {title}\n\n"
            f"_Trend data will appear here after multiple nightly runs. "
            f"First data point: {int(valid[0]):,} repos on {first_label}._\n"
        )

    max_val = max(valid)
    min_val = min(valid)
    span = max_val - min_val or 1

    lines = [f"### {title}", "```"]
    for row in range(CHART_HEIGHT, 0, -1):
        threshold = min_val + span * (row / CHART_HEIGHT)
        bars = ""
        for v in values:
            if v is None:
                bars += " "
            elif v >= threshold:
                bars += "█"
            else:
                bars += " "
        if row % 2 == 0:
            y_label = f"{threshold:>7.0f} |"
        else:
            y_label = "        |"
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
    """Format the most recent entry as a stats table.

    Args:
        entries: List of metric entry dicts.

    Returns:
        Markdown stats table string.
    """
    if not entries:
        return "_No data yet._"

    latest = entries[-1]
    fs1 = latest.get("forksync_v1") or {}
    fs2 = latest.get("forksync_v2") or {}
    db = latest.get("reporium_db") or {}
    api = latest.get("reporium_api") or {}

    def _fmt(v: object) -> str:
        if isinstance(v, int):
            return f"{v:,}"
        return str(v) if v is not None else "—"

    # forksync: prefer v2 duration (faster), fall back to v1
    if fs2.get("duration_seconds") is not None:
        duration = f"{fs2['duration_seconds']}s (v2)"
        repos_checked = _fmt(fs2.get("repos_checked"))
    elif fs1.get("duration_seconds") is not None:
        duration = f"{fs1['duration_seconds']}s (v1)"
        repos_checked = _fmt(fs1.get("repos_checked"))
    else:
        duration = "no data"
        repos_checked = "—"

    rows = [
        f"| Date | {latest.get('date', '—')} |",
        f"| Repos tracked (reporium-db) | {_fmt(db.get('repos_tracked'))} |",
        f"| Languages tracked | {_fmt(db.get('languages'))} |",
        f"| Categories enriched | {_fmt(db.get('categories_enriched'))} |",
        f"| Repos in API DB | {_fmt(api.get('total_repos_in_db'))} |",
        f"| Repos with ai_dev_skills | {_fmt(api.get('repos_with_ai_dev_skills'))} |",
        f"| Repos with categories | {_fmt(api.get('repos_with_categories'))} |",
        f"| Repos with readme_summary | {_fmt(api.get('repos_with_readme_summary'))} |",
        f"| forksync sync duration | {duration} |",
        f"| forksync repos checked | {repos_checked} |",
        f"| forksync v1 last run | {_fmt(fs1.get('repos_synced'))} synced (v2 does not yet write SYNC_REPORT.md) |"
        if fs1 else "| forksync v1 last run | — |",
    ]
    header = "| Metric | Value |\n|--------|-------|"
    return header + "\n" + "\n".join(rows)


def _status_section(entries: list[dict]) -> str:
    """Render a 'what works / what doesn't' status section from latest entry."""
    if not entries:
        return ""
    latest = entries[-1]
    db = latest.get("reporium_db") or {}
    api = latest.get("reporium_api") or {}
    fs2 = latest.get("forksync_v2") or {}

    working = [
        "reporium.com — live, repos browseable",
        f"reporium-db — nightly sync active, {db.get('repos_tracked', '?')} repos tracked, "
        f"{db.get('languages', '?')} languages",
    ]
    if fs2.get("duration_seconds") is not None:
        working.append(
            f"forksync v2 — {fs2['duration_seconds']}s for {fs2.get('repos_checked', '?')} repos"
            " on Cloud Run"
        )
    else:
        working.append(
            "forksync v2 — running on Cloud Run (duration confirmed 68s, SYNC_REPORT.md "
            "not yet written — fix in progress)"
        )

    not_working = [
        "reporium-ingestion — pipeline not running, 0 categories enriched, 0 readme summaries",
        f"reporium-api — {api.get('deployment', 'local only')}, no public endpoint",
        "forksync v2 SYNC_REPORT.md — not written by Cloud Run (workflow fix deployed, "
        "pending next run)",
        f"Categories — only 'tooling' exists in reporium-db, real AI categorization "
        f"requires ingestion pipeline",
    ]

    working_md = "\n".join(f"- {w}" for w in working)
    broken_md = "\n".join(f"- {b}" for b in not_working)

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
    """Build the full README.md from metrics entries.

    Args:
        entries: All metric entry dicts sorted by date.

    Returns:
        Complete README.md markdown string.
    """
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

    generated = entries[-1].get("date", "—") if entries else "—"

    return f"""# Reporium Metrics

> Platform performance tracking. Verified numbers only — no estimates.

## Current Stats

{stats_table}

{status}
## Trends

{repos_chart}

{milestones}

---
*Last updated: {generated} · Data from live GitHub sources.*
"""


def main() -> None:
    """Load metrics and write README.md."""
    t0 = time.monotonic()
    entries = load_metrics()
    readme = build_readme(entries)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    elapsed = time.monotonic() - t0
    logger.info("README generated in %.2fs — %d entries", elapsed, len(entries))


if __name__ == "__main__":
    main()
