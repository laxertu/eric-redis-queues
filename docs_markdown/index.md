# Eric Redis queues documentation

Redis support for eric-sse [https://laxertu.github.io/eric](https://laxertu.github.io/eric)

Example of usage:

> from eric_sse.prefabs import SSEChannel

> from eric_redis_queues import RedisConnectionsRepository

> c = SSEChannel(connections_repository=RedisConnectionsRepository())

* [Reference](docs.md)
  * [`AbstractRedisQueue`](docs.md#eric_redis_queues.AbstractRedisQueue)
  * [`RedisQueue`](docs.md#eric_redis_queues.RedisQueue)
  * [`BlockingRedisQueue`](docs.md#eric_redis_queues.BlockingRedisQueue)
  * [`RedisConnectionsRepository`](docs.md#eric_redis_queues.RedisConnectionsRepository)
  * [`RedisSSEChannelRepository`](docs.md#eric_redis_queues.RedisSSEChannelRepository)
