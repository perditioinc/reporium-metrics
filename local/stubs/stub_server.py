"""Single-file OSS stub for every HTTP dependency collect.py reaches.

Stands in for the two live cloud surfaces collect.py uses on this branch
(stdlib only -- $0, no pip installs, runs fully offline):

1. GitHub raw  (https://raw.githubusercontent.com/<repo>/main/<path>)
     GET /perditioinc/forksync/main/SYNC_REPORT.md
     GET /perditioinc/reporium-db/main/data/index.json
   The smoke runner redirects collect.GITHUB_RAW_BASE here.

2. reporium-api  (the Cloud Run service behind REPORIUM_API_URL)
     GET /metrics/latest

Dates are templated to "today" (UTC) so collect.py's prior-month skip and
duplicate-date guards behave exactly as they would against live sources.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TODAY_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

SYNC_REPORT = f"""# Fork Sync Report
**perditioinc's GitHub Forks** · {TODAY} 12:00 UTC · 68s

## Machine-readable fields
- date: {TODAY}
- duration_seconds: 68
- repos_checked: 818
- repos_synced: 201
- already_current: 265
- api_calls_used: 937
- errors: 0
- peak_concurrency: 50
"""

INDEX_JSON = {
    "meta": {"total": 1939, "last_updated": TODAY_ISO, "version": "1.0.0"},
    "categories": {"llm": 300, "rag": 100, "tooling": 800, "unknown": 50},
    "languages": {f"lang{i}": 10 for i in range(41)},
}

METRICS_LATEST = {
    "repos_tracked": 1732,
    "languages": 40,
    "source": "reporium-api /metrics/latest",
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: str, content_type: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, code: int, obj: object) -> None:
        self._send(code, json.dumps(obj), "application/json")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path

        if path == "/perditioinc/forksync/main/SYNC_REPORT.md":
            self._send(200, SYNC_REPORT, "text/plain; charset=utf-8")
        elif path == "/perditioinc/reporium-db/main/data/index.json":
            self._json(200, INDEX_JSON)
        elif path == "/metrics/latest":
            self._json(200, METRICS_LATEST)
        elif path == "/healthz":
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "not found", "path": path})

    def log_message(self, fmt: str, *args: object) -> None:
        print("stub %s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print(f"stub_server listening on :8080 (date={TODAY})")
    server.serve_forever()
