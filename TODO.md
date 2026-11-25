# TODO

## Connections per waiting stream

Each waiting `wait_pop()` holds a Redis connection (BLPOP). If that becomes a limit (`maxclients`, 10000 by default),
consider Pub/Sub wake-ups (one connection per process, tried on branch history of #12). Measure first with the
planned eric-api Locust scenarios.

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
