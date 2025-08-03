Eric Redis queues documentation
===============================

A Redis implementation of persistence layer of eric-sse: https://laxertu.github.io/eric/docs.html#persistence


Example of usage:


  from eric_sse.prefabs import SSEChannel

  from eric_redis_queues import RedisConnectionsRepository

  c = SSEChannel(connections_repository=RedisConnectionsRepository())


.. toctree::
   :maxdepth: 2

   docs
