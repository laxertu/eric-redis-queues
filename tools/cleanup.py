from redis import Redis

r = Redis()
for k in r.scan_iter('*'):
    r.delete(k)

"""
from eric_redis_queues.prefabs import RedisSSEChannelRepository

cr = RedisSSEChannelRepository()
for c in cr.load():
    cr.delete(c.id)
"""