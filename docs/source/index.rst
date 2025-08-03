Eric Redis queues documentation
===============================

Redis support for eric-sse https://laxertu.github.io/eric

Example of usage:


  from eric_sse.prefabs import SSEChannel

  from eric_redis_queues import RedisConnectionsRepository

  c = SSEChannel(connections_repository=RedisConnectionsRepository())


.. toctree::
   :maxdepth: 2

   docs
