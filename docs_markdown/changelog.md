# Changelog

## 3.0.0 (unreleased)

* Requires eric-sse 3.0.0
* BREAKING: `RedisConnectionRepository`, `RedisSSEChannelRepository`, `RedisListenerRepository`,
  `RedisQueuesRepository` and the connection factories are replaced by `redis_channel_repository_builder`, that
  wires everything to Redis through eric-sse’s `ChannelRepositoryBuilder` and can be further configured (listeners,
  error handlers) before `build()`
* BREAKING: `BlockingRedisQueue` and `RedisSSEChannelBlockingQueuesRepository` removed, see
  [Blocking queues]() below
* BREAKING: `RedisStorage` takes a `redis.Redis` client, so its connection details (credentials, TLS, pool,
  timeouts) are up to the application. The client must not decode responses. `RedisQueue`,
  `RedisQueueRepository` and `redis_channel_repository_builder` take a `RedisConnection` (host, port, db)
* BREAKING: keys layout changed: data persisted by 2.x is not readable by 3.x
* `RedisStorage` implements eric-sse 3 `KvStorage`: prefix searches match `*`, `?`, `[`, `]` literally and
  tolerate deletions while results are iterated
* `RedisQueue` implements eric-sse 3 `Queue`: `pop()` returns immediately, `pop(timeout)` and `wait_pop()`
  wait up to **timeout** seconds. When pickled, only its identity (connection data and queue id) is saved: messages
  stay in Redis. Queues with equal connection data share one client, so one connection pool
* Waits don’t poll and don’t hold a Redis connection: `push()` publishes a notification on a Pub/Sub channel
  (`eric-redis-queues:wake:<db>`, in the same transaction as the message), and one connection per process
  (named `eric-redis-queues:notifier`) wakes the waiters of the queue. `wait_pop()` waits natively, without a
  thread, so any number of streams can wait at once. A wait checks its queue once more when it times out, and all
  waits check again after the notifications connection is restored: a lost notification delays a message, never loses
  it. A message popped by a cancelled `wait_pop()` is put back at the head of its queue
* Added `RedisQueueRepository`: deleting a connection deletes its queued messages too, instead of leaving them in
  Redis
* Added integration tests running eric-sse contracts (channel repository, queue, channel, error handling) against a
  real Redis

### Blocking queues

In 2.x, `BlockingRedisQueue.pop()` waited until a message was pushed, with no time limit.

**Why it was dropped.** eric-sse 3 requires every queue’s `pop()` to return immediately, raising
`NoMessagesException` when empty: waiting is now chosen by the caller, passing a timeout. eric-sse itself relies on
it, so a queue waiting forever on `pop()`:

* hangs `AbstractChannel.deliver_next()` on an empty queue. Stopping the listener, removing the connection or deleting
  the channel can’t interrupt it, and it holds a Redis connection meanwhile. Called from async code, it freezes the
  event loop;
* breaks `DataProcessingChannel.process_queue()`, that pops until the queue is empty: after the last message it
  blocks the event loop forever, and messages already popped are never yielded.

**Same behaviour in 3.0.0.** Use `RedisQueue`, and wait where you consume. Waits are woken by Pub/Sub
notifications, so they don’t poll, and a message pushed while waiting is returned at once.

In async code, wait for the next message without blocking the event loop:

```default
connection.listener.start()
while True:
    try:
        msg = await channel.wait_next(connection.id, timeout=5)
    except NoMessagesException:
        continue  # Nothing within 5 seconds: wait again, or check whether to stop
    handle(msg)
```

or stream messages: `message_stream` starts the listener, waits for messages and ends when the listener stops:

```default
async for event in channel.message_stream(connection.id):
    ...
```

In sync code, run the same wait, so that the listener and error handlers are notified as with `deliver_next`:

```default
connection.listener.start()
while True:
    try:
        msg = asyncio.run(channel.wait_next(connection.id, timeout=5))
    except NoMessagesException:
        continue
    handle(msg)
```

or pop from the queue directly, bypassing the channel (listener `on_message` and error handlers are not called):

```default
msg = connection.queue.pop(timeout=5)
```

Timeouts replace “forever”: a consumer loop that waits again after each timeout behaves as the 2.x blocking queue,
and still gets the chance to stop.

Repositories created with `RedisSSEChannelBlockingQueuesRepository` are created with
`redis_channel_repository_builder(SSEChannel, redis_connection).build()`.
