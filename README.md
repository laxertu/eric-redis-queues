Redis support for eric-sse

A queue here is a Redis key value, where key is listener id and value is a list of Json data with messages information.

Example of usage:

    from eric_sse.prefabs import SSEChannel
    from eric_redis_queues.eric_redis_queues import RedisQueueFactory
    
    c = SSEChannel(queues_factory=RedisQueueFactory())
