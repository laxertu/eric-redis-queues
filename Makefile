RUN ?= poetry run
PYTHON ?= $(RUN) python

.PHONY: tests e2e_tests docs

# Runs the tests in tests/, as the CI does. They need a Redis, configured with REDIS_HOST, REDIS_PORT and REDIS_DB
# (default db 15), and are skipped if it is not reachable.
tests:
	$(PYTHON) -m unittest discover -s tests -t . -v

# Persists a channel and dispatches messages (load), delivers them from another process (run), then deletes what
# load persisted (cleanup), also when run fails. Redis is configured with REDIS_HOST, REDIS_PORT and REDIS_DB.
e2e_tests:
	@cmd=$$($(PYTHON) -m e2e_tests.load) && echo "$$cmd" && \
	$(PYTHON) -m e2e_tests.run $$(echo "$$cmd" | cut -d' ' -f4-); status=$$?; \
	$(PYTHON) -m e2e_tests.cleanup && exit $$status

# Regenerates docs_html and docs_markdown from docs/source, see docs/update_docs.sh. Needs the doctools group:
# poetry install --with doctools
docs:
	cd docs && $(RUN) bash update_docs.sh
