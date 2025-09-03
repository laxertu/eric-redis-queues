import sys

from eric_sse.exception import NoMessagesException, InvalidListenerException
from eric_redis_queues import RedisConnection
from eric_redis_queues.repository import RedisSSEChannelRepository

redis_connection = RedisConnection()
channel_repository = RedisSSEChannelRepository(redis_connection=redis_connection)

try:
    channel_id = sys.argv[1]
    l_id = sys.argv[2]
    channels = {ch.id: ch for ch in channel_repository.load_all()}
    ch = channels[channel_id]

    for x in ch.get_connections():
        print(x.id)

    #exit(0)
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

