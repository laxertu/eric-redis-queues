import sys

from eric_sse.exception import NoMessagesException, InvalidListenerException
from eric_redis_queues import RedisConnection
from eric_redis_queues.repository import RedisSSEChannelRepository

redis_connection = RedisConnection()
channel_repository = RedisSSEChannelRepository(redis_connection=redis_connection)

try:
    #python run.py 7e54511e-ec70-4b35-9c27-0a9c89b824cf ef696ea5-ddba-42d8-8c42-859fd4b26e66
    #channel_id = '6afcf504-5b6e-4327-871f-17812f965797'
    #l_id = 'b2128f18-d047-4d85-9da1-caae89b19fa9'
    channel_id = sys.argv[1]
    l_id = sys.argv[2]
    channels = {ch.id: ch for ch in channel_repository.load_all()}
    ch = channels[channel_id]

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

