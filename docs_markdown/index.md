# Eric Redis queues documentation

A Redis implementation of persistence layer of eric-sse:

* [Persistence layer documentation](https://laxertu.github.io/eric/persistence.html)
* An example of [microservice](https://pypi.org/project/eric-api/) based on this project
* Also [here](https://github.com/laxertu/eric-redis-queues/tree/master/e2e_tests) there is a simple flow for testing purposes

# Reference

Redis support for eric-sse: [`RedisStorage`](#eric_redis_queues.RedisStorage) persists channels, connections, listeners and queues,
[`RedisQueue`](#eric_redis_queues.RedisQueue) keeps messages. See [`eric_redis_queues.repository.redis_channel_repository_builder()`](#eric_redis_queues.repository.redis_channel_repository_builder).

### PREFIX_STORAGE *= 'eric-redis-queues:kv:'*

Default key prefix of [`RedisStorage`](#eric_redis_queues.RedisStorage).

### PREFIX_MESSAGES *= 'eric-redis-queues:m'*

Key prefix of [`RedisQueue`](#eric_redis_queues.RedisQueue) message lists.

### *class* RedisConnection

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

RedisConnection(host: str = ‘127.0.0.1’, port: int = 6379, db: int = 0)

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0)

* **Parameters:**
  * **host** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))
  * **port** ([*int*](https://docs.python.org/3/builtins/functions.html#int))
  * **db** ([*int*](https://docs.python.org/3/builtins/functions.html#int))
* **Return type:**
  None

### *class* RedisStorage

Bases: [`KvStorage`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage)

[`KvStorage`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage) backed by Redis. Values are pickled.

* **Parameters:**
  * **redis_connection** – Defaults to a local Redis, database 0. Shares the client of queues with equal connection data.
  * **prefix** – Prepended to every key. Prefixes of storages sharing a database must not be prefixes of each other.

#### \_\_init_\_(redis_connection=None, prefix='eric-redis-queues:kv:')

* **Parameters:**
  * **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection) *|* *None*)
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

Durable queue keeping pickled messages in a Redis list. Pickling it saves only its connection data and id.

[`pop()`](#eric_redis_queues.RedisQueue.pop) without timeout returns immediately, with a timeout it waits with
[BLPOP](https://redis.io/docs/latest/commands/blpop/). [`wait_pop()`](#eric_redis_queues.RedisQueue.wait_pop) runs BLPOP on an async client, so it
holds no thread, but holds a Redis connection while waiting. Queues with equal connection data share one client
per event loop.

* **Parameters:**
  * **redis_connection** – Defaults to a local Redis, database 0.
  * **queue_id** – Defaults to a new uuid.

#### \_\_init_\_(redis_connection=None, queue_id=None)

* **Parameters:**
  * **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection) *|* *None*)
  * **queue_id** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str) *|* *None*)

#### pop(timeout=0)

Next message from the queue.

* **Parameters:**
  **timeout** ([*float*](https://docs.python.org/3/builtins/functions.html#float)) – Seconds to wait for a message. With 0 it returns immediately.
* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any)

Raises a [`NoMessagesException`](https://laxertu.github.io/eric/reference/exceptions.html#eric_sse.exception.NoMessagesException) if no message is available, after waiting
**timeout** seconds.

#### *async* wait_pop(timeout)

Waits for the next message without blocking the event loop.

The default implementation runs [`pop()`](#eric_redis_queues.RedisQueue.pop) with **timeout** in a worker thread, so it takes one thread
per waiting call. Override it with a native async wait when possible.

* **Parameters:**
  **timeout** ([*float*](https://docs.python.org/3/builtins/functions.html#float)) – Seconds to wait for a message.
* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any)

Raises a [`NoMessagesException`](https://laxertu.github.io/eric/reference/exceptions.html#eric_sse.exception.NoMessagesException) if no message arrives within **timeout**.

#### purge()

Deletes all its messages.

* **Return type:**
  None

<a id="module-eric_redis_queues.repository"></a>

### *class* RedisQueueRepository

Bases: [`KvQueueRepository`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvQueueRepository)[[`RedisQueue`](#eric_redis_queues.RedisQueue)]

Creates, persists and loads [`RedisQueue`](#eric_redis_queues.RedisQueue) instances.

Queues are stored as they are: only their identity (connection data and queue id) is serialised, their messages
stay in Redis. Deleting a queue deletes its messages too, that would be left in Redis otherwise.

* **Parameters:**
  * **redis_connection** – Connection of the queues it creates.
  * **storage** – Storage for queues identity, keyed by connection id.

#### \_\_init_\_(redis_connection, storage)

* **Parameters:**
  * **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))
  * **storage** ([*KvStorage*](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.repository.KvStorage))

#### delete(connection_id)

Deletes a queue given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str))

### redis_channel_repository_builder(channel_class, redis_connection=None, prefix=None)

Returns a [`ChannelRepositoryBuilder`](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.builder.ChannelRepositoryBuilder) persisting everything in Redis:

```default
repository = redis_channel_repository_builder(SSEChannel, RedisConnection(host='localhost')).build()
```

It can be further configured before building, e.g. with listeners or error handlers.

* **Parameters:**
  * **channel_class** ([*type*](https://docs.python.org/3/builtins/functions.html#type) *[**C* *]*) – e.g. [`SSEChannel`](https://laxertu.github.io/eric/reference/prefabs.html#eric_sse.prefabs.SSEChannel).
  * **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection) *|* *None*) – Used by queues, and by the storage of everything else. Defaults to a local Redis,
    database 0.
  * **prefix** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str) *|* *None*) – Key prefix of the storage, see [`RedisStorage`](#eric_redis_queues.RedisStorage).
* **Return type:**
  [*ChannelRepositoryBuilder*](https://laxertu.github.io/eric/reference/persistence.html#eric_sse.builder.ChannelRepositoryBuilder)[*C*]

* [Changelog](changelog.md)
