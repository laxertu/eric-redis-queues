Redis support for eric-sse

*Installation*

pip install eric-redis-queues

*Usage*

```python
from redis import Redis
from eric_sse.prefabs import SSEChannel
from eric_redis_queues.repository import redis_channel_repository_builder

# Any redis-py client, configured as the application needs (credentials, TLS, pool, ...), without decode_responses
client = Redis(host='127.0.0.1', port=6379, db=0)

# Channels, connections, listeners and queues persisted in Redis; messages kept in Redis lists
repository = redis_channel_repository_builder(SSEChannel, client).build()
```

The returned builder is an eric-sse `ChannelRepositoryBuilder`, so it can be further configured (listeners, error
handlers) before `build()`.

*Migrating from 2.x*

* `RedisConnectionRepository`, `RedisSSEChannelRepository`, `RedisListenerRepository` and the connection factories
  are replaced by `redis_channel_repository_builder`.
* `BlockingRedisQueue` and `RedisSSEChannelBlockingQueuesRepository` are removed: in eric-sse 3 waiting is up to the
  caller, e.g. `await channel.wait_next(connection_id, timeout)`. See the
  [changelog](docs/source/changelog.rst#blocking-queues) for why, and how to get the same behaviour.
* `RedisConnection` is removed: `RedisStorage`, `RedisQueue`, `RedisQueueRepository` and
  `redis_channel_repository_builder` take a `redis.Redis` client.
* Keys layout changed: data persisted by 2.x is not readable by 3.x.

*Tests*

Integration tests run eric-sse contracts against a real Redis. Only `eric-redis-queues:*` keys are deleted.

```
REDIS_HOST=127.0.0.1 REDIS_PORT=6379 REDIS_DB=15 python -m pytest tests
```

Tests are skipped if Redis is not reachable.

*Related packages*

* https://pypi.org/project/eric-sse/ Base project

Documentation: https://laxertu.github.io/eric-redis-queues/
