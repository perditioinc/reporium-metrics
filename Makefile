# Root passthrough to the local OSS substrate (local/).
# Additive, local only, $0. Does not touch production or CI.
#
#   make local-up      start Postgres + stub, wait for healthy
#   make local-seed    show seeded knowledge-graph edge counts
#   make local-smoke   run real collect.py + generate.py against local stubs
#   make local-down    stop containers (keep volumes)
#   make local-clean   full teardown including volumes

.PHONY: local-up local-seed local-smoke local-down local-clean

local-up:
	$(MAKE) -C local up

local-seed:
	$(MAKE) -C local seed

local-smoke:
	$(MAKE) -C local smoke

local-down:
	$(MAKE) -C local down

local-clean:
	$(MAKE) -C local clean
