import sys
from eric_redis_queues.prefabs import RedisSSEChannelsRepository, RedisStorageEngine
from eric_sse.exception import NoMessagesException, InvalidListenerException

try:
    channel_id = sys.argv[1]
    l_id = sys.argv[2]
    repo = RedisSSEChannelsRepository(RedisStorageEngine(prefix='c'))
    channels = {ch.id: ch for ch in repo.load_all()}
    ch = channels[channel_id]
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

