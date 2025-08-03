# Reference

### *class* AbstractRedisQueue

Bases: `PersistableQueue`, `ABC`

#### \_\_init_\_(listener_id, host='127.0.0.1', port=6379, db=0)

* **Parameters:**
  **listener_id** (*str*)

#### *property* kv_key *: str*

The key to use when persisting object

#### *property* kv_value_as_dict

Returns value that will be persisted as a dictionary.

#### setup_by_dict(setup)

Does de necessary setup of object given its persisted values

* **Parameters:**
  **setup** (*dict*)

### *class* RedisQueue

Bases: [`AbstractRedisQueue`](#eric_redis_queues.AbstractRedisQueue)

#### pop()

Next message from the queue.

Raises a `eric_sse.exception.NoMessagesException` if the queue is empty.

* **Return type:**
  *Any* | None

#### push(msg)

* **Parameters:**
  **msg** (*MessageContract*)
* **Return type:**
  None

### *class* BlockingRedisQueue

Bases: [`RedisQueue`](#eric_redis_queues.RedisQueue)

#### pop()

Next message from the queue.

Raises a `eric_sse.exception.NoMessagesException` if the queue is empty.

* **Return type:**
  *Any* | None

### *class* RedisConnectionsRepository

Bases: `ConnectionRepositoryInterface`

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0)

#### create_queue(listener_id)

Returns a concrete Queue instance.

* **Parameters:**
  **listener_id** (*str*) – Corresponding listener id
* **Return type:**
  *Queue*

#### load_all()

Returns an Iterable of all persisted connections

* **Return type:**
  *Iterable*[*Connection*]

#### load(channel_id)

Returns an Iterable of all persisted connections of a given channel

* **Parameters:**
  **channel_id** (*str*)
* **Return type:**
  *Iterable*[*Connection*]

#### persist(channel_id, connection)

* **Parameters:**
  * **channel_id** (*str*)
  * **connection** (*Connection*)
* **Return type:**
  None

#### delete(channel_id, listener_id)

Removes a persisted `eric_sse.connection.PersistableConnection` given its correspondant listener id

* **Parameters:**
  * **channel_id** (*str*)
  * **listener_id** (*str*)

### *class* RedisSSEChannelRepository

Bases: `ChannelRepositoryInterface`

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0)

#### load()

Returns an Iterable of all persisted objects of correspondant concrete implementation.

* **Return type:**
  *Iterable*[*SSEChannel*]

#### persist(persistable)

* **Parameters:**
  **persistable** (*SSEChannel*)

#### delete(key)

* **Parameters:**
  **key** (*str*)

#### delete_listener(channel_id, listener_id)

* **Parameters:**
  * **channel_id** (*str*)
  * **listener_id** (*str*)
* **Return type:**
  None
