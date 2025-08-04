# Eric Redis queues documentation

A Redis implementation of persistence layer of eric-sse: [https://laxertu.github.io/eric/docs.html#persistence](https://laxertu.github.io/eric/docs.html#persistence)

# Reference

### *class* AbstractRedisQueue

Bases: [`PersistableQueue`](https://laxertu.github.io/eric/docs.html#eric_sse.persistence.PersistableQueue), [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

#### \_\_init_\_(listener_id, host='127.0.0.1', port=6379, db=0)

* **Parameters:**
  **listener_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))

#### *property* kv_key *: [str](https://docs.python.org/3/library/stdtypes.html#str)*

The key to use when persisting object

#### *property* kv_value_as_dict

Returns value that will be persisted as a dictionary.

#### setup_by_dict(setup)

Does de necessary setup of object given its persisted values

* **Parameters:**
  **setup** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict))

### *class* RedisQueue

Bases: [`AbstractRedisQueue`](#eric_redis_queues.AbstractRedisQueue)

#### pop()

Next message from the queue.

Raises a [`NoMessagesException`](https://laxertu.github.io/eric/docs.html#eric_sse.exception.NoMessagesException) if the queue is empty.

* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any) | None

### *class* BlockingRedisQueue

Bases: [`RedisQueue`](#eric_redis_queues.RedisQueue)

Implements a blocking queue. See **pop()** documentation

#### pop()

Behaviour relies on [https://redis.io/docs/latest/commands/blpop/](https://redis.io/docs/latest/commands/blpop/) , so calls to it with block program execution until a new message is pushed.

* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any) | None

### *class* AbstractRedisConnectionRepository

Bases: [`ConnectionRepositoryInterface`](https://laxertu.github.io/eric/docs.html#eric_sse.persistence.ConnectionRepositoryInterface), [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0)

#### *abstract* create_queue(listener_id)

Returns a concrete Queue instance.

* **Parameters:**
  **listener_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Corresponding listener id
* **Return type:**
  [*AbstractRedisQueue*](#eric_redis_queues.AbstractRedisQueue)

#### load_all()

Returns an Iterable of all persisted connections

* **Return type:**
  [*Iterable*](https://docs.python.org/3/library/typing.html#typing.Iterable)[[*Connection*](https://laxertu.github.io/eric/docs.html#eric_sse.connection.Connection)]

#### load(channel_id)

Returns an Iterable of all persisted connections of a given channel

* **Parameters:**
  **channel_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
* **Return type:**
  [*Iterable*](https://docs.python.org/3/library/typing.html#typing.Iterable)[[*Connection*](https://laxertu.github.io/eric/docs.html#eric_sse.connection.Connection)]

#### delete(channel_id, listener_id)

Deletes a listener given its channel id and listener id.

* **Parameters:**
  * **channel_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
  * **listener_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))

### *class* RedisConnectionsRepository

Bases: [`AbstractRedisConnectionRepository`](#eric_redis_queues.AbstractRedisConnectionRepository)

#### create_queue(listener_id)

Returns a concrete Queue instance.

* **Parameters:**
  **listener_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Corresponding listener id
* **Return type:**
  [*RedisQueue*](#eric_redis_queues.RedisQueue)

### *class* RedisBlockingQueuesRepository

Bases: [`AbstractRedisConnectionRepository`](#eric_redis_queues.AbstractRedisConnectionRepository)

#### create_queue(listener_id)

Creates a new blocking queue.

* **Parameters:**
  **listener_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
* **Return type:**
  [*BlockingRedisQueue*](#eric_redis_queues.BlockingRedisQueue)

### *class* RedisSSEChannelRepository

Bases: [`ChannelRepositoryInterface`](https://laxertu.github.io/eric/docs.html#eric_sse.persistence.ChannelRepositoryInterface)

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0, connection_factory='RedisConnectionsRepository')

* **Parameters:**
  * **host**
  * **port**
  * **db**
  * **connection_factory** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Connection factory name to use to connect to Redis. Accepted literals are **‘RedisConnectionsRepository’** and **‘RedisBlockingQueuesRepository’**

#### load()

Returns all channels from the repository.

* **Return type:**
  [*Iterable*](https://docs.python.org/3/library/typing.html#typing.Iterable)[[*SSEChannel*](https://laxertu.github.io/eric/docs.html#eric_sse.prefabs.SSEChannel)]
