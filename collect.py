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
import psycopg2
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

DATABASE_URL = os.getenv("DATABASE_URL", "")

FORKSYNC_REPO = os.getenv("FORKSYNC_REPO", "perditioinc/forksync")
REPORIUM_DB_REPO = os.getenv("REPORIUM_DB_REPO", "perditioinc/reporium-db")
REPORIUM_API_URL = os.getenv("REPORIUM_API_URL", "")


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
    """Parse SYNC_REPORT.md into a forksync_v1 metrics dict.

    Handles two formats:
    - Machine-readable field format: '- duration_seconds: 68'
    - Table format (v1): '| Synced | 201 |' with '· 14m 51s' header

    Args:
        text: Raw markdown text from SYNC_REPORT.md.

    Returns:
        Dict with parsed fields. Missing fields are omitted.
    """
    result: dict[str, Any] = {}

    def _find(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    # --- Machine-readable field format (forksync v2 reports) ---

    # Duration: "- duration_seconds: 68"
    raw = _find(r"-\s*duration[_ ]seconds[:\s]+(\d+)")
    if raw:
        result["duration_seconds"] = int(raw)

    raw = _find(r"-\s*repos[_ ]checked[:\s]+(\d+)")
    if raw:
        result["repos_checked"] = int(raw)

    raw = _find(r"-\s*repos[_ ]synced[:\s]+(\d+)")
    if raw:
        result["repos_synced"] = int(raw)

    raw = _find(r"-\s*already[_ ]current[:\s]+(\d+)")
    if raw:
        result["already_current"] = int(raw)

    raw = _find(r"-\s*api[_ ]calls[_ ]used[:\s]+(\d+)")
    if raw:
        result["api_calls_used"] = int(raw)

    raw = _find(r"-\s*errors[:\s]+(\d+)")
    if raw:
        result["errors"] = int(raw)

    raw = _find(r"-\s*peak[_ ]concurrency[:\s]+(\d+)")
    if raw:
        result["peak_concurrency"] = int(raw)

    # --- Table format (forksync v1) ---

    if "duration_seconds" not in result:
        # Duration from header: "· 14m 51s" or "· 68s"
        m_dur = re.search(r"·\s*(?:(\d+)m\s+)?(\d+)s(?:\b|$)", text)
        if m_dur:
            minutes = int(m_dur.group(1)) if m_dur.group(1) else 0
            seconds = int(m_dur.group(2))
            result["duration_seconds"] = minutes * 60 + seconds

    if "repos_synced" not in result:
        m_synced = re.search(r"Synced\s*\|\s*(\d+)", text)
        if m_synced:
            result["repos_synced"] = int(m_synced.group(1))

    if "repos_checked" not in result:
        counts = re.findall(r"\|\s*[\w\s✅⏭️⚠️🗄️⬆️]+\s*\|\s*(\d+)\s*\|", text)
        if counts:
            result["repos_checked"] = sum(int(c) for c in counts)

    if "api_calls_used" not in result:
        m_calls = re.search(r"API calls used[*\s]*:?[*\s]*(\d+)", text, re.IGNORECASE)
        if m_calls:
            result["api_calls_used"] = int(m_calls.group(1))

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
    """Parse reporium-db index.json into a reporium_db metrics dict.

    Args:
        data: Parsed index.json content.

    Returns:
        Dict with repos_tracked, languages (count), categories_enriched, last_updated.
    """
    meta = data.get("meta", {})
    languages = data.get("languages", {})
    categories = data.get("categories", {})

    # categories_enriched: only count if there are meaningful categories
    # (the reporium-db partitioner tags all repos as "tooling" which is not
    # real enrichment — real enrichment comes from reporium-ingestion)
    real_cats = {k: v for k, v in categories.items() if k not in ("tooling", "unknown")}
    categories_enriched = len(real_cats)

    return {
        "repos_tracked": meta.get("total"),
        "languages": len(languages),
        "categories_enriched": categories_enriched,
        "last_updated": meta.get("last_updated"),
        "source": "data/index.json — live",
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
        return json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load %s: %s", target, exc)
        return []


def save_metrics(entries: list[dict]) -> None:
    """Atomically write metrics.json.

    Args:
        entries: Full list of metric entry dicts to write.
    """
    tmp = METRICS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    os.replace(tmp, METRICS_FILE)
    logger.info("Saved %d metrics entries", len(entries))


def collect_edge_counts(conn: Any) -> dict[str, int]:
    """Collect edge counts per type from the knowledge graph.

    Args:
        conn: An open psycopg2 connection.

    Returns:
        Dict mapping edge_type to count, e.g. {"DEPENDS_ON": 89, "COMPATIBLE_WITH": 1234}.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT edge_type, COUNT(*) FROM repo_edges GROUP BY edge_type ORDER BY edge_type"
        )
        return {row[0]: row[1] for row in cur.fetchall()}


async def collect(token: str) -> Optional[dict[str, Any]]:
    """Collect today's platform metrics from live sources.

    Skips if today's entry already exists. Uses null for unavailable fields.

    Schema:
      - forksync_v1: from SYNC_REPORT.md (written by v1 locally or v2 via workflow)
      - forksync_v2: null until Cloud Run writes it
      - reporium_db: from data/index.json
      - reporium_api: null (local-only, not auto-collectable)

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

    # --- Fetch forksync SYNC_REPORT.md ---
    forksync_v1: Optional[dict] = None
    forksync_text = await _fetch_raw(token, FORKSYNC_REPO, "SYNC_REPORT.md")
    if forksync_text:
        report_date = _report_date(forksync_text)
        parsed = parse_sync_report(forksync_text)
        if parsed:
            # Only use if from current month (stale older data is misleading)
            if report_date and report_date[:7] < today[:7]:
                logger.info(
                    "SYNC_REPORT.md is from %s (prior month, today %s) — skipping",
                    report_date,
                    today,
                )
            else:
                forksync_v1 = parsed
                forksync_v1["source"] = "SYNC_REPORT.md — live"
                logger.info("Parsed SYNC_REPORT.md (dated %s)", report_date or "unknown")
        else:
            logger.warning("SYNC_REPORT.md present but no parseable fields found")

    if forksync_v1 is None:
        logger.warning("No fresh forksync data available — using null")

    # --- Fetch reporium-db index.json ---
    reporium_db: Optional[dict] = None
    index_text = await _fetch_raw(token, REPORIUM_DB_REPO, "data/index.json")
    if index_text:
        try:
            reporium_db = parse_index_json(json.loads(index_text))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse index.json: %s", exc)

    if reporium_db is None:
        logger.warning("reporium-db index.json unavailable — using null")

    # --- Fetch reporium-api /metrics/latest ---
    reporium_api: Optional[dict] = None
    if REPORIUM_API_URL:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(f"{REPORIUM_API_URL}/metrics/latest")
                resp.raise_for_status()
                reporium_api = resp.json()
                reporium_api["source"] = "reporium-api /metrics/latest — live"
                logger.info(
                    "Fetched reporium-api metrics: %d repos tracked",
                    reporium_api.get("repos_tracked", 0),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("reporium-api unavailable: %s — using null", exc)
    else:
        logger.info("REPORIUM_API_URL not set — skipping API metrics")

    # --- Fetch knowledge graph edge counts ---
    # graph_health tracks total edges and per-type counts so reporium-audit can
    # detect regressions (e.g. DEPENDS_ON dropping to 0 after a schema change).
    graph_health: Optional[dict] = None
    if REPORIUM_API_URL:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    f"{REPORIUM_API_URL}/graph/edges",
                    params={"limit": 1},  # Minimal payload — we only need counts
                )
                resp.raise_for_status()
                data = resp.json()
                total = data.get("total", 0)
                edge_types = data.get("edgeTypes", [])
                # Fetch per-type counts
                type_counts: dict[str, int] = {}
                for et in edge_types:
                    try:
                        r2 = await client.get(
                            f"{REPORIUM_API_URL}/graph/edges",
                            params={"limit": 1, "edge_type": et},
                        )
                        r2.raise_for_status()
                        type_counts[et] = r2.json().get("total", 0)
                    except Exception:
                        type_counts[et] = -1  # -1 = fetch failed

                depends_on_count = type_counts.get("DEPENDS_ON", 0)
                graph_health = {
                    "total_edges": total,
                    "edge_type_counts": type_counts,
                    "depends_on_zero": depends_on_count == 0,
                    "source": "reporium-api /graph/edges — live",
                }
                if depends_on_count == 0:
                    logger.warning(
                        "DEPENDS_ON edge count is 0 — repo_dependencies may be empty or "
                        "build_knowledge_graph.py has not been run since the fix"
                    )
                else:
                    logger.info(
                        "Graph health: total=%d, DEPENDS_ON=%d", total, depends_on_count
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch graph edge counts: %s", exc)

    # --- Collect knowledge graph edge counts directly from DB ---
    edge_counts: Optional[dict[str, int]] = None
    if DATABASE_URL:
        try:
            db_conn = psycopg2.connect(DATABASE_URL)
            try:
                edge_counts = collect_edge_counts(db_conn)
            finally:
                db_conn.close()
            logger.info("Collected edge counts: %s", edge_counts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not collect edge counts: %s", exc)
    else:
        logger.info("DATABASE_URL not set — skipping edge count collection")

    entry: dict[str, Any] = {
        "date": today,
        "forksync_v1": forksync_v1,
        "forksync_v2": None,
        "reporium_db": reporium_db,
        "reporium_api": reporium_api,
        "graph_health": graph_health,
        "edge_counts": edge_counts,
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
