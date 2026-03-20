# Reporium Metrics

<!-- perditio-badges-start -->
[![Tests](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-metrics)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Platform performance tracking. Verified numbers only — no estimates.

## Current Stats

| Metric | Value |
|--------|-------|
| Date | 2026-03-20 |
| Repos tracked (reporium-db) | 826 |
| Languages tracked | 29 |
| Categories enriched | 0 |
| Repos in API DB | — |
| Repos with ai_dev_skills | — |
| Repos with categories | — |
| Repos with readme_summary | — |
| forksync sync duration | 143s (v1) |
| forksync repos checked | 792 |
| forksync v1 last run | 0 synced (v2 does not yet write SYNC_REPORT.md) |

## Status

### Working
- reporium.com — live, repos browseable
- reporium-db — nightly sync active, 826 repos tracked, 29 languages
- forksync v2 — running on Cloud Run (duration confirmed 68s, SYNC_REPORT.md not yet written — fix in progress)

### Not Working
- reporium-ingestion — pipeline not running, 0 categories enriched, 0 readme summaries
- reporium-api — local only, no public endpoint
- forksync v2 SYNC_REPORT.md — not written by Cloud Run (workflow fix deployed, pending next run)
- Categories — only 'tooling' exists in reporium-db, real AI categorization requires ingestion pipeline

## Trends

### Repos Tracked Over Time
```
    826 |  █
        |  █
    824 |  █
        |  █
    822 |  █
        |  █
    820 |  █
        |  █
        +---
         03-17 03-19 03-20
```

## Milestones

| Date | Achievement |
|------|-------------|
| 2026-03-20 | **reporium-api deployed to Cloud Run — 826 repos accessible via public REST API** |
| 2026-03-20 | Neon PostgreSQL (pgvector) provisioned, all 13 tables migrated |
| 2026-03-20 | reporium-events Pub/Sub system live, forksync + reporium-db publishing events |
| 2026-03-20 | reporium-audit nightly health checks, perditio-devkit shared tooling |
| 2026-03-20 | Reporium suite badges and build counters on all repos |
| 2026-03-17 | **forksync v2 launched on Cloud Run — 68s for 818 repos, 91% faster than v1 (was 13 min)** |
| 2026-03-17 | Cloud Run + Redis + VPC connector deployed for forksync |


---
*Last updated: 2026-03-20 · Data from live GitHub sources.*
