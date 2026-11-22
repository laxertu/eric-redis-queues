"""Deletes every channel persisted by e2e_tests.load, with its connections and messages."""
from e2e_tests.load import build_repository

repository = build_repository()
for channel in list(repository.load_all()):
    repository.delete(channel.id)
