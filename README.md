# Reporium Metrics

> Platform performance tracking. Verified numbers only — no estimates.

## Current Stats

| Metric | Value |
|--------|-------|
| Date | 2026-03-17 |
| Repos tracked (reporium-db) | 818 |
| Languages tracked | 29 |
| Categories enriched | 0 |
| Repos in API DB | 702 |
| Repos with ai_dev_skills | 571 |
| Repos with categories | 0 |
| Repos with readme_summary | 0 |
| forksync sync duration | 68s (v2) |
| forksync repos checked | 818 |
| forksync repos synced | 201 |

## Status

### Working
- reporium.com — live, repos browseable
- reporium-db — nightly sync active, 818 repos tracked, 29 languages
- forksync v2 — 68s for 818 repos on Cloud Run

### Not Working
- reporium-ingestion — pipeline not running, 0 categories enriched, 0 readme summaries
- reporium-api — local only — no cloud deployment, no public endpoint
- forksync v2 SYNC_REPORT.md — not written by Cloud Run (workflow fix deployed, pending next run)
- Categories — only 'tooling' exists in reporium-db, real AI categorization requires ingestion pipeline

## Trends

### Repos Tracked Over Time
```
    819 | 
        | 
    819 | 
        | 
    818 | 
        | 
    818 | 
        | 
        +-
         03-17
```

## Milestones

| Date | Achievement |
|------|-------------|
| 2026-03-17 | **forksync v2: 68s for 805 repos - 91% faster than v1 (was 13 min)** |
| 2026-03-17 | Reporium v1.0.0: 805 repos tracked, 702 AI-enriched, 12 categories |
| 2026-03-17 | Cloud Run + Redis + VPC connector deployed for forksync |


---
*Last updated: 2026-03-17 · Data from live GitHub sources.*
