Redis support for eric-sse (https://laxertu.github.io/eric/)

A queue here is a Redis key value where key is listener id and value is a list of Jsons with messages information.

Example of usage::

    from eric_sse.prefabs import SSEChannel
    from eric_redis_queues.eric_redis_queues import RedisQueueFactory
    
    c = SSEChannel()
    c.set_queues_factory(RedisQueueFactory())


