# Design decisions Claude disagrees with

## 1. Everything is pickled

Messages, listeners and channel data are stored as pickled Python objects.

- `pickle.loads` runs code: anyone who can write to Redis can run code in every process reading it.
- Stored data depends on Python class paths: renaming or moving a listener class breaks loading. Only Python can read it.
- Alternative: JSON for messages (type, payload, id) and channel data.

## 2. Queues carry their own connection details

- No passwords or TLS: adding them to `RedisConnection` would store the password in Redis, as queues are pickled with it.
- Shared clients live in module-level caches: never closed, timeouts, pool size and retries not configurable.
- Alternative: queues store only their id; the repository or builder owns the clients and gives them to loaded queues.

## 3. Lookups scan the whole database

`RedisStorage.fetch_by_prefix` uses SCAN, which walks every key of the database. Loading N channels means N full scans
(one per channel's connections). Slow with a big database, or one shared with other data.

- Alternative: a Redis set or hash per namespace as an index.

## Also: put-back after a cancelled wait

It protects only a narrow window: a message can still be lost after it's popped, e.g. while sent to a browser that
disconnects. Delivery stays at most once. Either state it and drop the put-back, or use eric's `ReliableQueue` for
acknowledgements.
