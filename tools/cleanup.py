from eric_redis_queues import RedisSSEChannelRepository
from redis import Redis

r = Redis()
for k in r.scan_iter('*'):
    r.delete(k)

cr = RedisSSEChannelRepository()
for c in cr.load_all():
    cr.delete(c.id)