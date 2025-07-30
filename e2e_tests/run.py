import sys
from eric_redis_queues import RedisConnectionsRepository
from eric_sse.prefabs import SSEChannel
from eric_sse.exception import NoMessagesException, InvalidListenerException

try:
    l_id = "eric-redis-queues:l:d8aac843-8838-4245-b9ad-7233da88ba66".split(":")[2]
    print(l_id)

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
