# Eric Redis queues documentation

A Redis implementation of persistence layer of eric-sse:

* [Persistence layer documentation](https://laxertu.github.io/eric/persistence.html)
* An example of [microservice](https://pypi.org/project/eric-api/) based on this project

# Reference

### *class* RedisConnection

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

RedisConnection(host: str = ‘127.0.0.1’, port: int = 6379, db: int = 0)

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0)

* **Parameters:**
  * **host** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
  * **port** ([*int*](https://docs.python.org/3/library/functions.html#int))
  * **db** ([*int*](https://docs.python.org/3/library/functions.html#int))
* **Return type:**
  None

### *class* AbstractRedisQueue

Bases: [`Queue`](https://laxertu.github.io/eric/channels.html#eric_sse.queues.Queue), [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

#### \_\_init_\_(redis_connection, queue_id=None)

* **Parameters:**
  * **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))
  * **queue_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *|* *None*)

### *class* RedisQueue

Bases: [`AbstractRedisQueue`](#eric_redis_queues.AbstractRedisQueue)

#### pop()

Next message from the queue.

Raises a [`NoMessagesException`](https://laxertu.github.io/eric/exceptions.html#eric_sse.exception.NoMessagesException) if the queue is empty.

* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any) | None

### *class* BlockingRedisQueue

Bases: [`AbstractRedisQueue`](#eric_redis_queues.AbstractRedisQueue)

Implements a blocking queue. See **pop()** documentation

#### pop()

Behaviour relies on [https://redis.io/docs/latest/commands/blpop/](https://redis.io/docs/latest/commands/blpop/) , so calls to it with block program execution until a new message is pushed.

* **Return type:**
  [*Any*](https://docs.python.org/3/library/typing.html#typing.Any) | None

<a id="module-eric_redis_queues.repository"></a>

### *class* RedisStorage

Bases: [`KvStorage`](https://laxertu.github.io/eric/persistence.html#eric_sse.repository.KvStorage)

#### \_\_init_\_(prefix, redis_connection)

* **Parameters:**
  * **prefix** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
  * **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))

### *class* RedisListenerRepository

Bases: [`ListenerRepositoryInterface`](https://laxertu.github.io/eric/persistence.html#eric_sse.interfaces.ListenerRepositoryInterface)

#### \_\_init_\_(redis_connection)

* **Parameters:**
  **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))

#### load(connection_id)

Loads a listener given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
* **Return type:**
  [*MessageQueueListener*](https://laxertu.github.io/eric/channels.html#eric_sse.listener.MessageQueueListener)

#### delete(connection_id)

Deleted a listener given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))

### *class* AbstractRedisConnectionFactory

Bases: [`ConnectionsFactory`](https://laxertu.github.io/eric/channels.html#eric_sse.connection.ConnectionsFactory), [`ABC`](https://docs.python.org/3/library/abc.html#abc.ABC)

#### \_\_init_\_(redis_connection)

* **Parameters:**
  **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))

### *class* RedisConnectionFactory

Bases: [`AbstractRedisConnectionFactory`](#eric_redis_queues.repository.AbstractRedisConnectionFactory)

#### create(listener=None)

Creates a connection

* **Parameters:**
  **listener** ([*MessageQueueListener*](https://laxertu.github.io/eric/channels.html#eric_sse.listener.MessageQueueListener)) – If provided, assigns a concrete listener
* **Return type:**
  [*Connection*](https://laxertu.github.io/eric/channels.html#eric_sse.connection.Connection)

### *class* RedisBlockingQueuesConnectionFactory

Bases: [`AbstractRedisConnectionFactory`](#eric_redis_queues.repository.AbstractRedisConnectionFactory)

#### create(listener=None)

Creates a connection

* **Parameters:**
  **listener** ([*MessageQueueListener*](https://laxertu.github.io/eric/channels.html#eric_sse.listener.MessageQueueListener)) – If provided, assigns a concrete listener
* **Return type:**
  [*Connection*](https://laxertu.github.io/eric/channels.html#eric_sse.connection.Connection)

### *class* RedisQueuesRepository

Bases: [`QueueRepositoryInterface`](https://laxertu.github.io/eric/persistence.html#eric_sse.interfaces.QueueRepositoryInterface)

#### \_\_init_\_(redis_connection)

* **Parameters:**
  **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))

#### load(connection_id)

Loads a queue given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))
* **Return type:**
  [*AbstractRedisQueue*](#eric_redis_queues.AbstractRedisQueue)

#### delete(connection_id)

Deletes a queue given the connection id it belongs to.

* **Parameters:**
  **connection_id** ([*str*](https://docs.python.org/3/library/stdtypes.html#str))

### *class* RedisConnectionRepository

Bases: [`ConnectionRepository`](https://laxertu.github.io/eric/persistence.html#eric_sse.repository.ConnectionRepository)

#### \_\_init_\_(redis_connection)

* **Parameters:**
  **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))

### *class* RedisSSEChannelRepository

Bases: [`SSEChannelRepository`](https://laxertu.github.io/eric/prefabs.html#eric_sse.prefabs.SSEChannelRepository)

#### \_\_init_\_(redis_connection)

* **Parameters:**
  **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))

### *class* RedisSSEChannelBlockingQueuesRepository

Bases: [`SSEChannelRepository`](https://laxertu.github.io/eric/prefabs.html#eric_sse.prefabs.SSEChannelRepository)

#### \_\_init_\_(redis_connection)

* **Parameters:**
  **redis_connection** ([*RedisConnection*](#eric_redis_queues.RedisConnection))
