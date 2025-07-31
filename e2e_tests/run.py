import sys
from eric_redis_queues import RedisConnectionsRepository
from eric_sse.prefabs import SSEChannel
from eric_sse.exception import NoMessagesException, InvalidListenerException

try:
    l_id = sys.argv[1]

    ch = SSEChannel(connections_repository=RedisConnectionsRepository())
    ch.open()
    ch.get_listener(listener_id=l_id).start()

except IndexError:
    print("Usage: python run.py <listener id>")
    sys.exit(0)
except InvalidListenerException:
    print("Invalid id")
    sys.exit(0)

while True:
    try:
        x = ch.deliver_next(l_id)
        print(x)
        print(x.type, x.payload)
    except NoMessagesException:
        print('done')
        exit(0)
