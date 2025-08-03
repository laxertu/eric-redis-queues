A Redis implementation of persistence layer of eric-sse: [https://laxertu.github.io/eric/docs.html#persistence](https://laxertu.github.io/eric/docs.html#persistence)

# Reference

### *class* AbstractRedisQueue

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

#### pop()

Next message from the queue.

Raises a `eric_sse.exception.NoMessagesException` if the queue is empty.

* **Return type:**
  *Any* | None

### *class* BlockingRedisQueue

#### pop()

Next message from the queue.

Raises a `eric_sse.exception.NoMessagesException` if the queue is empty.

* **Return type:**
  *Any* | None

### *class* RedisConnectionsRepository

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

#### delete(channel_id, listener_id)

Deletes a listener given its channel id and listener id.

* **Parameters:**
  * **channel_id** (*str*)
  * **listener_id** (*str*)

### *class* RedisSSEChannelRepository

#### \_\_init_\_(host='127.0.0.1', port=6379, db=0)

#### load()

Returns all channels from the repository.

* **Return type:**
  *Iterable*[*SSEChannel*]
