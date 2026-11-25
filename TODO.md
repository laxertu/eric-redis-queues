# TODO

## Pub/Sub wake-ups (branch `pubsub-wakeups`)

Implemented, not committed yet. Before merging, decide on:

- **Fan-out:** every process using the same Redis and database receives every push notification (a queue id), also
  for queues it is not waiting on. Traffic grows with pushes × processes. Alternative: subscribe per queue while it
  has waiters, at the cost of a subscribe round trip per wait.
- **Mixed versions:** consumers on the old BLPOP code still receive messages from new producers, but new consumers
  aren't woken by old producers (no notification): they find those messages only when their wait times out.
- **Shared Redis in tests:** `test_waits_recover_when_the_notifications_connection_is_lost` kills every connection
  named `eric-redis-queues:notifier` on the server, including other processes' (they reconnect by themselves).

## Release 3.0.0

- Changelog still says "3.0.0 (unreleased)": set the release date.
- eric-api must move to the `RedisConnection` API before or with the release, see eric-api `TODO.md`.

## Remove the error handling contract workaround

`RedisChannelErrorHandlingTestCase` (tests/test_contracts.py) works around two contract issues reported in
laxertu/eric#53: it lowers the `eric_sse` logger level, and keeps the builder's default storage in memory for the
contract's unpicklable `BrokenQueue`. Remove both once eric-sse fixes the contract.

## Redis with credentials or TLS

`RedisConnection` only carries host, port and db: queues, and the storage when created through the builder, can't use
a Redis requiring a password or TLS. Add fields (e.g. username, password, ssl) if needed. Keep in mind that queues are
pickled with their `RedisConnection`, so a password would be stored in Redis.
