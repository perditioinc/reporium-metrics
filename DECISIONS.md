# Architecture Decisions

> Every major decision in the platform, with the problem it solved and the measured result.

---

## forksync v2 — Why We Rebuilt It

**Problem:** The v1 GitHub Actions workflow used the GitHub merge-upstream REST API
(`POST /repos/:owner/:repo/merge-upstream`). Repos appeared synced but the API was
silently failing — forks would show "synced" in the response but their default branch
was not actually updated.

**What we tried:** Debugging the REST API with verbose logging. The API confirmed success
but the commits weren't there.

**What we chose:** Replaced with `gh repo sync` — the official GitHub CLI command.
It syncs via the same mechanism as the GitHub UI "Sync fork" button. If it reports
success, the sync happened.

**Measured result:** 201 repos verified synced on first clean v2 run. All can be confirmed
by checking commit history.

---

## Cloud Run — Why Not GitHub Actions

**Problem:** GitHub Actions has a 6-minute timeout for free accounts. The v1 sync took
13 minutes (14m 51s recorded in SYNC_REPORT.md from 2026-03-17). This meant every nightly
run was timing out partway through.

**What we tried:** Splitting into batches across multiple workflow runs. This caused
ordering issues and partial syncs.

**What we chose:** Cloud Run with a 900-second timeout and streaming response. The workflow
triggers the Cloud Run endpoint via curl and keeps the connection open for the full duration.

**Measured result:** v2 completes in 68 seconds for 818 repos. The 900s timeout is never
reached.

---

## Redis — Why We Added Caching

**Problem:** The compare API (GitHub REST compare two commits) was returning stale responses
on repeated calls within the same run. This caused repos to appear behind when they were
already current.

**What we chose:** Redis with ETag-based caching. Each compare response is cached with
the ETag from GitHub. On the next run, we send `If-None-Match` — GitHub returns 304 if
nothing changed, saving both an API call and parsing time.

**Measured result:** API calls per run reduced. The 50-concurrent compare pass runs
significantly faster on subsequent runs where most repos haven't changed.

---

## GraphQL — Why Not REST for Fork Fetching

**Problem:** The REST API required one call per fork to fetch metadata (stars, upstream,
pushed_at). With 818 forks, that is 818 API calls just for the initial fetch — consuming
16% of the hourly rate limit before any syncing started.

**What we chose:** GitHub GraphQL API. A single paginated query fetches all fork metadata.
818 repos requires approximately 9 API calls total (100 repos per page).

**Measured result:** Fork metadata fetch: 9 API calls vs 818. Frees up rate limit for
the actual compare and sync operations.

---

## What Is Not Working (as of 2026-03-17)

| Component | Status | Reason |
|-----------|--------|--------|
| reporium-ingestion | Not running | Pipeline not deployed to cloud |
| AI categories | 0 enriched | Depends on ingestion pipeline |
| readme_summary | 0 populated | Depends on ingestion pipeline (Ollama) |
| reporium-api | Local only | Not deployed to cloud |
| SYNC_REPORT.md | Stale (v1 data) | Cloud Run does not commit to GitHub (fix deployed) |
