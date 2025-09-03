from eric_redis_queues import RedisConnection
from eric_redis_queues.repository import RedisSSEChannelRepository

repo = RedisSSEChannelRepository(redis_connection=RedisConnection())

for channel in repo.load_all():
    repo.delete(channel.id)
