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
        entries = json.loads(path.read_text())
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
        # Add y-axis label on every other row
        if row % 2 == 0:
            y_label = f"{threshold:>7.0f} |"
        else:
            y_label = "        |"
        lines.append(f"{y_label}{bars}")

    # X-axis separator
    lines.append("        +" + "-" * len(values))

    # X-axis labels (use just dates, 6-char spacing)
    step = max(1, len(labels) // 6)
    x_line = "         "
    for i, label in enumerate(labels):
        if i % step == 0:
            x_line += label[-5:]  # last 5 chars of date
            x_line += " "
    lines.append(x_line.rstrip())
    lines.append("```")
    return "\n".join(lines)


def _improvement_callout(entries: list[dict]) -> str:
    """Check for notable improvements and render a callout block.

    Args:
        entries: All metric entry dicts.

    Returns:
        Markdown callout string, or empty string if none.
    """
    for entry in entries:
        note = (entry.get("forksync") or {}).get("note", "")
        if "91%" in note:
            duration = (entry.get("forksync") or {}).get("duration_seconds")
            repos = (entry.get("forksync") or {}).get("repos_checked")
            if duration is not None and repos is not None:
                return (
                    f"> **91% improvement**: forksync v2 syncs {repos:,} repos in {duration}s "
                    f"(was ~13 minutes). Same results, 11x faster.\n"
                )
    return ""


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
    forksync = latest.get("forksync") or {}
    reporium = latest.get("reporium") or {}

    rows = [
        f"| Date | {latest.get('date', '—')} |",
        f"| Repos tracked | {reporium.get('repos_tracked', '—'):,} |"
        if isinstance(reporium.get("repos_tracked"), int)
        else f"| Repos tracked | {reporium.get('repos_tracked', '—')} |",
        f"| Repos enriched | {reporium.get('repos_enriched', '—')} |",
        f"| Categories | {reporium.get('categories', '—')} |",
        f"| forksync duration | {forksync.get('duration_seconds', '—')}s |",
        f"| forksync repos | {forksync.get('repos_checked', '—')} |",
        f"| Peak concurrency | {forksync.get('peak_concurrency', '—')} |",
        f"| API calls | {forksync.get('api_calls', '—')} |",
    ]
    header = "| Metric | Value |\n|--------|-------|"
    return header + "\n" + "\n".join(rows)


def _milestones_section() -> str:
    """Read and include MILESTONES.md content.

    Returns:
        Markdown milestones section string.
    """
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

    # forksync duration trend
    durations: list[Optional[float]] = [
        e.get("forksync", {}).get("duration_seconds") if e.get("forksync") else None
        for e in entries
    ]

    # repos tracked trend
    repos_tracked: list[Optional[float]] = [
        float(e.get("reporium", {}).get("repos_tracked", 0))
        if e.get("reporium") and e["reporium"].get("repos_tracked") is not None
        else None
        for e in entries
    ]

    duration_chart = _ascii_chart(durations, dates, "forksync Sync Duration (seconds)")
    repos_chart = _ascii_chart(repos_tracked, dates, "Repos Tracked Over Time")
    stats_table = _current_stats(entries)
    milestones = _milestones_section()
    callout = _improvement_callout(entries)

    generated = entries[-1].get("date", "—") if entries else "—"

    return f"""# Reporium Metrics

> Platform performance tracking over time. Concrete numbers that speak for themselves.

{callout}
## Current Stats

{stats_table}

## Trends

{duration_chart}

{repos_chart}

{milestones}

---
*Last updated: {generated} · Data from live GitHub workflows.*
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
