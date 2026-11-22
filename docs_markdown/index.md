# Eric Redis queues documentation

A Redis implementation of persistence layer of eric-sse:

* [Persistence layer documentation](https://laxertu.github.io/eric/persistence.html)
* An example of [microservice](https://pypi.org/project/eric-api/) based on this project
* Also [here](https://github.com/laxertu/eric-redis-queues/tree/master/e2e_tests) there is a simple flow for testing purposes

# Reference

Redis support for eric-sse.

* [`RedisStorage`](#eric_redis_queues.RedisStorage): a [`KvStorage`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage), to persist channels, connections, listeners and queues;
* [`RedisQueue`](#eric_redis_queues.RedisQueue): a durable [`Queue`](https://laxertu.github.io/eric/reference/entities.html#eric_sse.queues.Queue), whose messages live in a Redis list.

Both take a `redis.Redis` client: connection details (host, credentials, TLS, pool, timeouts) are up to the
application. See [`eric_redis_queues.repository.redis_channel_repository_builder()`](#eric_redis_queues.repository.redis_channel_repository_builder) to wire them together.

### PREFIX_STORAGE *= 'eric-redis-queues:kv:'*

Default key prefix of [`RedisStorage`](#eric_redis_queues.RedisStorage).

### PREFIX_MESSAGES *= 'eric-redis-queues:m'*

Key prefix of the lists holding [`RedisQueue`](#eric_redis_queues.RedisQueue) messages.

### *class* RedisStorage

Bases: [`KvStorage`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage)

[`KvStorage`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage) backed by Redis. Values are pickled.

* **Parameters:**
  * **client** – Must not decode responses (`decode_responses=False`, the default).
  * **prefix** – Prepended to every key. Storages sharing a Redis database must have prefixes that are not
    prefixes of each other.

#### \_\_init_\_(client, prefix='eric-redis-queues:kv:')

* **Parameters:**
  * **client** (*Redis*)
  * **prefix** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))

#### fetch_by_prefix(prefix)

Search by KV prefix. An empty prefix returns all items.

Implementations must tolerate deletions of fetched keys while the result is being iterated.

* **Parameters:**
  **prefix** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))
* **Return type:**
  [*Iterable*](https://docs.python.org/3/library/typing.html#typing.Iterable)[[*Any*](https://docs.python.org/3/library/typing.html#typing.Any)]

#### upsert(key, value)

Updates or inserts a value given its corresponding key

* **Parameters:**
  * **key** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))
  * **value** ([*Any*](https://docs.python.org/3/library/typing.html#typing.Any))

#### fetch_one(key)

Return value correspondant to key

* **Parameters:**
  **key** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))
* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any)

#### delete(key)

Idempotent deletion. Do not throw an error on invalid key

* **Parameters:**
  **key** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))

### *class* RedisQueue

Bases: [`Queue`](https://laxertu.github.io/eric/reference/entities.html#eric_sse.queues.Queue)

Durable queue: messages are pickled and kept in a Redis list, so several processes can share it.

It can’t be pickled, as its client can’t: persist it with
[`RedisQueueRepository`](#eric_redis_queues.repository.RedisQueueRepository), that stores its id and gives it a client when loading it.

[`pop()`](#eric_redis_queues.RedisQueue.pop) without timeout returns immediately, as eric-sse requires. With a timeout it waits for a message,
relying on [BLPOP](https://redis.io/docs/latest/commands/blpop/), so it doesn’t poll. This replaces
`BlockingRedisQueue` of previous versions: callers choose whether to wait, e.g. with
[`wait_next()`](https://laxertu.github.io/eric/reference/entities.html#eric_sse.entities.AbstractChannel.wait_next) or `queue.pop(timeout=...)`.
[`wait_pop()`](https://laxertu.github.io/eric/reference/entities.html#eric_sse.queues.Queue.wait_pop) is inherited: it runs [`pop()`](#eric_redis_queues.RedisQueue.pop) in a worker thread.

* **Parameters:**
  * **client** – Must not decode responses (`decode_responses=False`, the default). A `socket_timeout`, if set,
    must be longer than the waits.
  * **queue_id** – Identifies the Redis list. Defaults to a new uuid.

#### \_\_init_\_(client, queue_id=None)

* **Parameters:**
  * **client** (*Redis*)
  * **queue_id** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str) *|* *None*)

#### pop(timeout=0)

Next message from the queue.

* **Parameters:**
  **timeout** ([*float*](https://docs.python.org/3/builtins/functions.html#float)) – Seconds to wait for a message. With 0 it returns immediately.
* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any)

Raises a [`NoMessagesException`](https://laxertu.github.io/eric/reference/exceptions.html#eric_sse.exception.NoMessagesException) if no message is available, after waiting
**timeout** seconds.

#### purge()

Deletes all its messages.

* **Return type:**
  None

<a id="module-eric_redis_queues.repository"></a>

### *class* RedisQueueRepository

Bases: [`QueueRepositoryInterface`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.interfaces.QueueRepositoryInterface)[[`RedisQueue`](#eric_redis_queues.RedisQueue)]

Creates, persists and loads [`RedisQueue`](#eric_redis_queues.RedisQueue) instances.

Only queue ids are stored: loaded queues get **client**. Deleting a queue deletes its messages too.

* **Parameters:**
  * **client** – Given to the queues it creates and loads, see [`RedisQueue`](#eric_redis_queues.RedisQueue).
  * **storage** – Storage for queue ids, keyed by connection id.

#### \_\_init_\_(client, storage)

* **Parameters:**
  * **client** (*Redis*)
  * **storage** ([*KvStorage*](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage))

#### create()

Creates a new queue. It is not persisted.

* **Return type:**
  [*RedisQueue*](#eric_redis_queues.RedisQueue)

#### load(connection_id)

Loads a queue given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))
* **Return type:**
  [*RedisQueue*](#eric_redis_queues.RedisQueue)

#### persist(connection_id, queue)

Persists queue and assign to connection.

* **Parameters:**
  * **connection_id** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))
  * **queue** ([*RedisQueue*](#eric_redis_queues.RedisQueue))

#### delete(connection_id)

Deletes a queue given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))

### redis_channel_repository_builder(channel_class, client, prefix=None)

Returns a [`ChannelRepositoryBuilder`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.builder.ChannelRepositoryBuilder) persisting everything in Redis:

```default
repository = redis_channel_repository_builder(SSEChannel, Redis(host='localhost')).build()
```

It can be further configured before building, e.g. with listeners or error handlers.

* **Parameters:**
  * **channel_class** ([*type*](https://docs.python.org/3/builtins/functions.html#type) *[**C* *]*) – e.g. [`SSEChannel`](https://laxertu.github.io/eric/reference/prefabs.html#eric_sse.prefabs.SSEChannel).
  * **client** (*Redis*) – Must not decode responses (`decode_responses=False`, the default).
  * **prefix** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str) *|* *None*) – Key prefix of the storage, see [`RedisStorage`](#eric_redis_queues.RedisStorage).
* **Return type:**
  [*ChannelRepositoryBuilder*](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.builder.ChannelRepositoryBuilder)[*C*]

* [Changelog](changelog.md)
