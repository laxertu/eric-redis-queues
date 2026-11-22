PYTHON ?= poetry run python

.PHONY: e2e_tests

# Persists a channel and dispatches messages (load), delivers them from another process (run), then deletes what
# load persisted (cleanup), also when run fails. Redis is configured with REDIS_HOST, REDIS_PORT and REDIS_DB.
e2e_tests:
	@cmd=$$($(PYTHON) -m e2e_tests.load) && echo "$$cmd" && \
	$(PYTHON) -m e2e_tests.run $$(echo "$$cmd" | cut -d' ' -f4-); status=$$?; \
	$(PYTHON) -m e2e_tests.cleanup && exit $$status
