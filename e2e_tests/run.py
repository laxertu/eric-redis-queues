import sys

from eric_sse.exception import NoMessagesException, InvalidListenerException
from eric_redis_queues import RedisConnection
from eric_redis_queues.repository import RedisSSEChannelRepository, RedisSSEChannelBlockingQueuesRepository

redis_connection = RedisConnection()
channel_repository = RedisSSEChannelRepository(redis_connection=redis_connection)

try:
    channel_id = sys.argv[1]
    l_id = sys.argv[2]
    repo_type = sys.argv[3]

    channels = {ch.id: ch for ch in channel_repository.load_all()}
    ch = channels[channel_id]

    if repo_type == 'default':
        channel_repository = RedisSSEChannelRepository(redis_connection=redis_connection)
    elif repo_type == 'blocking':
        channel_repository = RedisSSEChannelBlockingQueuesRepository(redis_connection=redis_connection)

    for x in ch.get_connections():
        print(x.id)

    ch.get_listener(listener_id=l_id).start()

    while True:
        try:
            x = ch.deliver_next(l_id)
            print("DELIVERED", x.type, x.payload)
        except NoMessagesException:
            print('done')
            exit(0)

except IndexError:
    print("Usage: python run.py <listener id>")
    sys.exit(0)
except KeyError:
    print("Invalid channel id")
except InvalidListenerException:
    print("Invalid listener id")
    sys.exit(0)

