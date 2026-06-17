# Local OSS substrate for reporium-metrics. $0, additive, local only.
# Usage: make up | seed | smoke | down | clean
#
# Run from this directory (local/) or via the root passthrough: `make -C local <target>`.

COMPOSE := docker compose

.PHONY: up down seed smoke clean logs

## up: start the stub service and wait until it is healthy
up:
	$(COMPOSE) up --wait stub

## seed: no external datastore on this branch; the stub serves fixed fixtures.
##       This target prints the fixtures the stub will return so a run is reproducible.
seed:
	$(COMPOSE) up --wait stub
	@echo "Stub fixtures (served at http://stub:8080):"
	$(COMPOSE) exec -T stub python -c "import stub_server,json; print('SYNC_REPORT.md repos_synced=201, duration=68'); print('index.json:', json.dumps(stub_server.INDEX_JSON['meta'])); print('/metrics/latest:', json.dumps(stub_server.METRICS_LATEST))"

## smoke: run the real collect.py + generate.py path against the local stub
smoke:
	$(COMPOSE) run --rm smoke

## logs: tail substrate logs
logs:
	$(COMPOSE) logs -f

## down: stop and remove containers (keeps named volumes)
down:
	$(COMPOSE) down

## clean: full teardown including volumes
clean:
	$(COMPOSE) down -v
