# Reporium Metrics

<!-- perditio-badges-start -->
[![Tests](https://github.com/perditioinc/reporium-metrics/actions/workflows/test.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/test.yml)
[![Nightly](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml/badge.svg)](https://github.com/perditioinc/reporium-metrics/actions/workflows/collect.yml)
![Last Commit](https://img.shields.io/github/last-commit/perditioinc/reporium-metrics)
![python](https://img.shields.io/badge/python-3.11%2B-3776ab)
![suite](https://img.shields.io/badge/suite-Reporium-6e40c9)
<!-- perditio-badges-end -->

> Platform performance tracking. Verified numbers only â€” no estimates.

## Current Stats

| Metric | Value |
|--------|-------|
| Date | 2026-04-15 |
| Repos tracked (reporium-db) | â€” |
| Languages tracked | â€” |
| Categories enriched | â€” |
| Repos in API DB | â€” |
| Languages (API) | â€” |
| forksync sync duration | no data |
| forksync repos checked | â€” |
| forksync repos synced | â€” |

## Status

### Working
- reporium.com â€” live, repos browseable
- reporium-db â€” nightly sync active, â€” repos tracked, â€” languages
- forksync v2 â€” running on Cloud Run (no SYNC_REPORT.md data available)
- reporium-api â€” deployed to Cloud Run (metrics not yet collected)

### Not Working
- reporium-ingestion â€” pipeline not running, 0 categories enriched
- AI categories â€” requires ingestion pipeline to generate real categorization

## Trends

### Repos Tracked Over Time
```
   1822 |                       █     
        |                   █████     
   1571 |            ████████████     
        |      ██████████████████     
   1320 |     ███████████████████     
        |     ███████████████████     
   1069 |     ███████████████████     
        |     ███████████████████     
        +-----------------------------
         03-17 03-22 03-26 03-30 04-03 04-07 04-11 04-15
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


## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| GraphQL over REST | REST API required 826 individual calls. GraphQL batch does it in 9. |
| Cloud Run for forksync | GitHub Actions timeout at 6min could not support 13min v1 runtime. |
| Redis for caching | ETag caching reduces redundant compare API calls. |
| Neon over Cloud SQL | Cloud SQL costs $7-10/month minimum. Neon free tier supports pgvector. |
| Partitioned JSON | Single dataset.json would be 50MB+ at 100K repos. Partitioned files let frontend load only what it needs. |
| Pub/Sub events | Decouples services â€” forksync and reporium-db publish events, API and audit consume them. |

---
*Last updated: 2026-04-15 Â· Data from live GitHub sources.*
