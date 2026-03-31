# Reporium Metrics

<!-- perditio-badges-start -->
[![Tests](https://github.com/perditioinc/reporium-metrics/actions/workflows/test.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/test.yml)
[![Nightly](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-metrics)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Platform performance tracking. Verified numbers only, no estimates.

This README is a historical snapshot of the metrics state captured on 2026-03-20. It should not be treated as the current live suite total without regenerating the metrics artifacts.

## Historical Snapshot: 2026-03-20

| Metric | Value |
|--------|-------|
| Date | 2026-03-31 |
| Repos tracked (reporium-db) | 1,573 |
| Languages tracked | 39 |
| Categories enriched | 0 |
| Repos in API DB | - |
| Languages (API) | - |
| forksync sync duration | 143s (v1) |
| forksync repos checked | 792 |
| forksync repos synced | 0 |

## Status

### Working
- reporium.com — live, repos browseable
- reporium-db — nightly sync active, 1573 repos tracked, 39 languages
- forksync v2 — 143s for 792 repos on Cloud Run, SYNC_REPORT.md committed via GitHub API
- reporium-api — deployed to Cloud Run (metrics not yet collected)

### Not Working
- reporium-ingestion: pipeline not running, 0 categories enriched
- AI categories: required the ingestion pipeline to generate real categorization

## Trends

These trend points reflect the March 2026 metrics history preserved in this file.

### Repos Tracked Over Time
```
   1573 |            ██
        |           ███
   1384 |     █████████
        |     █████████
   1196 |     █████████
        |     █████████
   1007 |     █████████
        |     █████████
        +--------------
         03-17 03-20 03-22 03-24 03-26 03-28 03-30
```

## Milestones

The milestones below are preserved as dated platform milestones, not current state assertions.

| Date | Achievement |
|------|-------------|
| 2026-03-20 | **reporium-api deployed to Cloud Run - 826 repos accessible via public REST API at that milestone** |
| 2026-03-20 | Neon PostgreSQL (pgvector) provisioned, all 13 tables migrated |
| 2026-03-20 | reporium-events Pub/Sub system planned and partially wired, with forksync + reporium-db as intended publishers at that milestone |
| 2026-03-20 | reporium-audit nightly health checks, perditio-devkit shared tooling |
| 2026-03-20 | Reporium suite badges and build counters on all repos |
| 2026-03-17 | **forksync v2 launched on Cloud Run - 68s for 818 repos, 91% faster than v1 (was 13 min)** |
| 2026-03-17 | Cloud Run + Redis + VPC connector deployed for forksync |

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| GraphQL over REST | At the March 2026 launch scale, REST API required 826 individual calls. GraphQL batch did it in 9. |
| Cloud Run for forksync | GitHub Actions timeout at 6min could not support 13min v1 runtime. |
| Redis for caching | ETag caching reduces redundant compare API calls. |
| Neon over Cloud SQL | Cloud SQL costs $7-10/month minimum. Neon free tier supports pgvector. |
| Partitioned JSON | Single `dataset.json` would be 50MB+ at 100K repos. Partitioned files let the frontend load only what it needs. |
| Pub/Sub events | Intended to decouple services; forksync and reporium-db were the planned publishers at this milestone, while downstream consumer integration was still evolving. |

---
*Historical snapshot last updated: 2026-03-20. Regenerate metrics artifacts before treating these values as current live state.*
