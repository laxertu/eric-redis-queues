import sys
from eric_redis_queues import RedisChannel
from eric_sse.exception import NoMessagesException, InvalidListenerException

try:
    l_id = sys.argv[1]

    ch = RedisChannel()
    ch.get_listener(listener_id=l_id).start_sync()

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
