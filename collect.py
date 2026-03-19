"""Collect nightly platform metrics and append to metrics.json."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

GITHUB_RAW_BASE = "https://raw.githubusercontent.com"
TIMEOUT = 15
METRICS_FILE = Path("metrics.json")

FORKSYNC_REPO = os.getenv("FORKSYNC_REPO", "perditioinc/forksync")
REPORIUM_DB_REPO = os.getenv("REPORIUM_DB_REPO", "perditioinc/reporium-db")


async def _fetch_raw(token: str, owner_repo: str, file_path: str) -> Optional[str]:
    """Fetch a raw file from GitHub.

    Args:
        token: GitHub PAT.
        owner_repo: e.g. 'perditioinc/forksync'.
        file_path: e.g. 'SYNC_REPORT.md'.

    Returns:
        Raw text content or None on failure.
    """
    url = f"{GITHUB_RAW_BASE}/{owner_repo}/main/{file_path}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch %s/%s: %s", owner_repo, file_path, exc)
        return None


def parse_sync_report(text: str) -> dict[str, Any]:
    """Parse SYNC_REPORT.md into a metrics dict using regex.

    Handles two formats:
    - Table format: "| ✅ Synced | 201 |" with "**API calls used**: 937"
      and header "· 14m 51s" for duration.
    - Field format: "- duration: 68s", "- repos_checked: 805" (legacy).

    Args:
        text: Raw markdown text from SYNC_REPORT.md.

    Returns:
        Dict with parsed fields. Missing fields are omitted.
    """
    result: dict[str, Any] = {}

    def _find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    # --- Table format (actual SYNC_REPORT.md from forksync) ---

    # Duration from header: "· 14m 51s" or "· 68s"
    m_dur = re.search(r"·\s*(?:(\d+)m\s+)?(\d+)s(?:\b|$)", text)
    if m_dur:
        minutes = int(m_dur.group(1)) if m_dur.group(1) else 0
        seconds = int(m_dur.group(2))
        result["duration_seconds"] = minutes * 60 + seconds

    # repos_synced from "✅ Synced | 201"
    m_synced = re.search(r"Synced\s*\|\s*(\d+)", text)
    if m_synced:
        result["repos_synced"] = int(m_synced.group(1))

    # repos_checked = sum of all status counts in the summary table
    counts = re.findall(r"\|\s*[\w\s✅⏭️⚠️🗄️⬆️]+\s*\|\s*(\d+)\s*\|", text)
    if counts:
        result["repos_checked"] = sum(int(c) for c in counts)

    # api_calls from "**API calls used**: 937 / ..."
    m_calls = re.search(r"API calls used[*\s]*:?[*\s]*(\d+)", text, re.IGNORECASE)
    if m_calls:
        result["api_calls"] = int(m_calls.group(1))

    # --- Field format (legacy / fallback) ---
    if "duration_seconds" not in result:
        raw = _find(r"-\s*duration[:\s]+(\d+)")
        if raw:
            result["duration_seconds"] = int(raw)

    if "repos_checked" not in result:
        raw = _find(r"-\s*repos[_ ]checked[:\s]+(\d+)")
        if raw:
            result["repos_checked"] = int(raw)

    raw_concurrency = _find(r"-\s*peak[_ ]concurrency[:\s]+(\d+)")
    if raw_concurrency:
        result["peak_concurrency"] = int(raw_concurrency)

    if "api_calls" not in result:
        raw = _find(r"-\s*api[_ ]calls[:\s]+(\d+)")
        if raw:
            result["api_calls"] = int(raw)

    if "repos_synced" not in result:
        raw = _find(r"-\s*repos[_ ]synced[:\s]+(\d+)")
        if raw:
            result["repos_synced"] = int(raw)

    raw_errors = _find(r"-\s*errors[:\s]+(\d+)")
    if raw_errors:
        result["errors"] = int(raw_errors)

    return result


def _report_date(text: str) -> Optional[str]:
    """Extract the date from a SYNC_REPORT.md header line.

    Args:
        text: Raw markdown text.

    Returns:
        Date string 'YYYY-MM-DD' or None if not found.
    """
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    return m.group(1) if m else None


def parse_index_json(data: dict) -> dict[str, Any]:
    """Parse reporium-db index.json into a metrics dict.

    Args:
        data: Parsed index.json content.

    Returns:
        Dict with repos_tracked, categories, last_updated.
    """
    meta = data.get("meta", {})
    categories = data.get("categories", {})
    result: dict[str, Any] = {
        "repos_tracked": meta.get("total"),
        "last_updated": meta.get("last_updated"),
    }
    # Only record category count if there are meaningful categories (not just "unknown"/"tooling")
    if len(categories) >= 2:
        result["categories"] = len(categories)
    else:
        result["categories"] = None
    # repos_enriched is not in index.json; will be carried forward from prior entries
    result["repos_enriched"] = None
    return result


def load_metrics(path: Optional[Path] = None) -> list[dict]:
    """Load existing metrics.json or return empty list.

    Args:
        path: Path to metrics.json. Defaults to module-level METRICS_FILE.

    Returns:
        List of metric entry dicts.
    """
    target = path if path is not None else METRICS_FILE
    if not target.exists():
        return []
    try:
        return json.loads(target.read_text())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load %s: %s", target, exc)
        return []


def save_metrics(entries: list[dict]) -> None:
    """Atomically write metrics.json.

    Args:
        entries: Full list of metric entry dicts to write.
    """
    tmp = METRICS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2))
    os.replace(tmp, METRICS_FILE)
    logger.info("Saved %d metrics entries", len(entries))


async def collect(token: str) -> Optional[dict[str, Any]]:
    """Collect today's platform metrics from live sources.

    Skips if today's entry already exists. Uses null for unavailable fields.

    Args:
        token: GitHub PAT.

    Returns:
        New entry dict, or None if today's entry already exists.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entries = load_metrics(METRICS_FILE)

    if any(e.get("date") == today for e in entries):
        logger.info("Today's entry (%s) already exists — skipping", today)
        return None

    t0 = time.monotonic()

    # Fetch forksync SYNC_REPORT.md — only use if the report is from today or yesterday
    forksync_text = await _fetch_raw(token, FORKSYNC_REPO, "SYNC_REPORT.md")
    forksync_data: Optional[dict] = None
    if forksync_text:
        report_date = _report_date(forksync_text)
        parsed = parse_sync_report(forksync_text)
        if parsed:
            if report_date and report_date < today[:7]:
                # Report is from a prior month — too stale to use
                logger.info(
                    "SYNC_REPORT.md is from %s (prior month, today %s) — skipping",
                    report_date,
                    today,
                )
            else:
                forksync_data = parsed
                logger.info(
                    "Parsed forksync SYNC_REPORT.md (dated %s)",
                    report_date or "unknown",
                )
        else:
            logger.warning("SYNC_REPORT.md present but no parseable fields found")
    if forksync_data is None:
        logger.warning("No fresh forksync data available — using null")

    # Fetch reporium-db index.json
    index_text = await _fetch_raw(token, REPORIUM_DB_REPO, "data/index.json")
    reporium_data: Optional[dict] = None
    if index_text:
        try:
            reporium_data = parse_index_json(json.loads(index_text))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse index.json: %s", exc)

    # Carry forward repos_enriched and categories from the most recent entry that has them
    if reporium_data is not None and entries:
        for prev in reversed(entries):
            prev_repo = prev.get("reporium") or {}
            if reporium_data.get("repos_enriched") is None and prev_repo.get("repos_enriched"):
                reporium_data["repos_enriched"] = prev_repo["repos_enriched"]
            if (reporium_data.get("categories") or 0) < 2 and (prev_repo.get("categories") or 0) >= 2:
                reporium_data["categories"] = prev_repo["categories"]
            if reporium_data.get("repos_enriched") and reporium_data.get("categories", 0) >= 2:
                break

    if reporium_data is None:
        logger.warning("reporium-db index.json unavailable — using null values")

    entry: dict[str, Any] = {
        "date": today,
        "forksync": forksync_data,
        "reporium": reporium_data,
    }

    entries.append(entry)
    save_metrics(entries)

    elapsed = time.monotonic() - t0
    logger.info("Collected metrics in %.2fs", elapsed)
    return entry


async def main() -> None:
    """CLI entry point for collect.py."""
    token = os.getenv("GH_TOKEN", "")
    if not token:
        raise ValueError("GH_TOKEN is required")
    entry = await collect(token)
    if entry:
        logger.info("New entry: %s", json.dumps(entry, default=str))
    else:
        logger.info("No new entry written")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
