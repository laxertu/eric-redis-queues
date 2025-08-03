from eric_redis_queues import RedisSSEChannelRepository

cr = RedisSSEChannelRepository()
for c in cr.load():
    cr.delete(c.id)