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

    Expected format: lines like "- Duration: 68s" or "- Repos checked: 805".
    Uses regex (not position-dependent) per spec.

    Args:
        text: Raw markdown text from SYNC_REPORT.md.

    Returns:
        Dict with parsed fields. Missing fields are omitted.
    """
    result: dict[str, Any] = {}

    def _find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    raw_duration = _find(r"-\s*duration[:\s]+(\d+)")
    if raw_duration is not None:
        result["duration_seconds"] = int(raw_duration)

    raw_checked = _find(r"-\s*repos[_ ]checked[:\s]+(\d+)")
    if raw_checked is not None:
        result["repos_checked"] = int(raw_checked)

    raw_concurrency = _find(r"-\s*peak[_ ]concurrency[:\s]+(\d+)")
    if raw_concurrency is not None:
        result["peak_concurrency"] = int(raw_concurrency)

    raw_calls = _find(r"-\s*api[_ ]calls[:\s]+(\d+)")
    if raw_calls is not None:
        result["api_calls"] = int(raw_calls)

    raw_synced = _find(r"-\s*repos[_ ]synced[:\s]+(\d+)")
    if raw_synced is not None:
        result["repos_synced"] = int(raw_synced)

    raw_errors = _find(r"-\s*errors[:\s]+(\d+)")
    if raw_errors is not None:
        result["errors"] = int(raw_errors)

    return result


def parse_index_json(data: dict) -> dict[str, Any]:
    """Parse reporium-db index.json into a metrics dict.

    Args:
        data: Parsed index.json content.

    Returns:
        Dict with repos_tracked, categories, last_updated.
    """
    meta = data.get("meta", {})
    return {
        "repos_tracked": meta.get("total"),
        "categories": len(data.get("categories", {})),
        "last_updated": meta.get("last_updated"),
    }


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

    # Fetch forksync SYNC_REPORT.md
    forksync_text = await _fetch_raw(token, FORKSYNC_REPO, "SYNC_REPORT.md")
    forksync_data: Optional[dict] = parse_sync_report(forksync_text) if forksync_text else None
    if forksync_data is None:
        logger.warning("forksync SYNC_REPORT.md unavailable — using null values")

    # Fetch reporium-db index.json
    index_text = await _fetch_raw(token, REPORIUM_DB_REPO, "data/index.json")
    reporium_data: Optional[dict] = None
    if index_text:
        try:
            reporium_data = parse_index_json(json.loads(index_text))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse index.json: %s", exc)

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
