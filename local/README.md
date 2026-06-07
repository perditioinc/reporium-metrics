# Local OSS Substrate

A self-contained, `$0`, OSS-only dev substrate that lets you run the real
`collect.py` + `generate.py` path on your machine with no cloud access and no
secrets. Additive and local only -- it never touches production, CI, or any
live cloud resource, and it mounts the source checkout **read-only** so a run
can never mutate your working tree.

## What it replaces

On this branch `collect.py` reaches two live cloud surfaces. Each gets a local
OSS stand-in:

| Live cloud dependency | What collect.py does | Local OSS substitute |
|-----------------------|----------------------|----------------------|
| GitHub raw (`raw.githubusercontent.com`) | fetch `forksync/main/SYNC_REPORT.md` and `reporium-db/main/data/index.json` | stdlib `http.server` stub (`local/stubs/stub_server.py`) serving both paths, with the report date templated to today (UTC) |
| reporium-api (Cloud Run) via `REPORIUM_API_URL` | `GET /metrics/latest` | same stub, returning the same JSON contract |

The stub is stdlib-only (no pip installs) and the smoke runner installs only the
app's own `requirements.txt`. Everything is free and runs fully offline.

## Quick start

From this directory (`local/`):

```sh
make up      # start the stub, wait until healthy
make seed    # print the fixtures the stub will serve
make smoke   # run the real collect.py + generate.py path against the stub
make clean   # full teardown (containers + volumes)
```

Or from the repo root via the passthrough:

```sh
make local-up
make local-smoke
make local-clean
```

## How the wiring works

Everything is plain env config that the app already reads -- `REPORIUM_API_URL`,
`FORKSYNC_REPO`, `REPORIUM_DB_REPO` -- pointed at the local stub in
`docker-compose.yml`.

The one exception is `GITHUB_RAW_BASE`, which `collect.py` defines as a module
constant rather than an env var. Rather than edit the app, the smoke runner
(`local/smoke.py`) redirects that single constant to the local stub at runtime.
This is the only piece of wiring not exposed as configuration, and it lives
entirely in the smoke runner, not in the application source.

## The smoke test

`local/smoke.py` drives the unmodified `collect.collect()` and
`generate.build_readme()` functions end to end and asserts on the real output:

- forksync metrics (duration, repos_synced) parsed from the stubbed `SYNC_REPORT.md`
- reporium-db `repos_tracked` / `languages` / `categories_enriched` parsed from `index.json`
- reporium-api `/metrics/latest` captured
- `metrics.json` persisted and `README.md` rendered from it

Outputs are written to a named volume (`/work`), never the read-only checkout.
Exit `0` = PASS.

## Config

Defaults are baked into `docker-compose.yml`, so nothing is required. To override,
copy `.env.example` to `.env`.
