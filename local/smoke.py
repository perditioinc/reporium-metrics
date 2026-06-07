"""Smoke test: exercise collect.py + generate.py real path against local OSS stubs.

This is a thin runner, NOT an app edit. The checkout is mounted read-only, so:
  - we import the real collect/generate modules unchanged
  - we redirect GITHUB_RAW_BASE (a module constant, not an env var) to the local
    stub via a one-line monkeypatch -- the single piece of wiring the app does
    not expose as configuration
  - everything else (REPORIUM_API_URL, FORKSYNC_REPO, REPORIUM_DB_REPO) is plain
    env config the app already reads
  - metrics.json / README.md are written into a writable /work dir, never the
    read-only source checkout

Exit 0 = PASS, non-zero = FAIL.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

WORK = Path(os.environ["SMOKE_WORK"])  # writable scratch, set by compose
WORK.mkdir(parents=True, exist_ok=True)
METRICS = WORK / "metrics.json"
README = WORK / "README.md"

# Start each run clean so the duplicate-date guard does not short-circuit.
if METRICS.exists():
    METRICS.unlink()
METRICS.write_text("[]", encoding="utf-8")

import collect  # noqa: E402  (import after env is set up)
import generate  # noqa: E402

# --- the one bit of wiring the app does not expose as env config -------------
collect.GITHUB_RAW_BASE = os.environ["GITHUB_RAW_BASE"]
# Point both modules at the writable metrics file.
collect.METRICS_FILE = METRICS
generate.METRICS_FILE = METRICS
# ----------------------------------------------------------------------------

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {msg}")
    if not cond:
        failures.append(msg)


async def run() -> None:
    token = os.environ.get("GH_TOKEN", "local-stub-token")

    # 1. Real collect path against local stubs (GitHub raw + reporium-api)
    entry = await collect.collect(token)
    check(entry is not None, "collect() returned a new entry")
    if entry is None:
        return

    # 2. GitHub-raw forksync surface parsed from stubbed SYNC_REPORT.md
    fs1 = entry["forksync_v1"]
    check(
        fs1 is not None and fs1["duration_seconds"] == 68,
        "forksync_v1 parsed from stubbed SYNC_REPORT.md (duration=68)",
    )
    check(
        fs1 is not None and fs1["repos_synced"] == 201,
        "forksync_v1 repos_synced=201",
    )

    # 3. GitHub-raw reporium-db surface parsed from stubbed index.json
    db = entry["reporium_db"]
    check(db is not None and db["repos_tracked"] == 1939, "reporium_db repos_tracked=1939")
    check(db is not None and db["languages"] == 41, "reporium_db languages=41")
    check(
        db is not None and db["categories_enriched"] == 2,
        "categories_enriched=2 (tooling/unknown excluded)",
    )

    # 4. reporium-api /metrics/latest surface captured
    api = entry["reporium_api"]
    check(api is not None and api["repos_tracked"] == 1732, "reporium_api /metrics/latest captured")

    # 5. metrics.json persisted exactly one entry
    persisted = json.loads(METRICS.read_text(encoding="utf-8"))
    check(len(persisted) == 1, "metrics.json persisted exactly one entry")

    # 6. Real generate path renders README from collected metrics
    entries = generate.load_metrics(METRICS)
    readme = generate.build_readme(entries)
    README.write_text(readme, encoding="utf-8")
    check("# Reporium Metrics" in readme, "generate.build_readme produced README")
    check("1,939" in readme, "README reflects collected repos_tracked (1,939)")


def main() -> int:
    asyncio.run(run())
    print()
    if failures:
        print(f"SMOKE RESULT: FAIL ({len(failures)} check(s) failed)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SMOKE RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
