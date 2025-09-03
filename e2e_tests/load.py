from eric_sse.message import SignedMessage, UniqueMessage, Message

from eric_redis_queues import RedisConnection
from eric_redis_queues.repository import (AbstractRedisConnectionFactory, RedisConnectionFactory,
                                          RedisBlockingQueuesConnectionFactory, RedisSSEChannelRepository)
from eric_sse.prefabs import SSEChannel

redis_connection = RedisConnection()
channel_repository = RedisSSEChannelRepository(redis_connection=redis_connection)

connection_factory = RedisConnectionFactory(redis_connection=redis_connection)
blocking_connection_factory = RedisBlockingQueuesConnectionFactory(redis_connection=redis_connection)

def do_test(my_connection_factory: AbstractRedisConnectionFactory):
    ch = SSEChannel(connections_factory=my_connection_factory)

    sm = SignedMessage(sender_id='admin', msg_type='test', msg_payload='hi there')
    um = UniqueMessage(message_id='mgs_id0001', sender_id='administrator',
                       message=Message(msg_type='test2', msg_payload={'a': 1}))
    m = Message(msg_type='testsimple', msg_payload='hi, simple')
    l = ch.add_listener()
    print(f'python run.py {ch.id} {l.id}')
    print("")
    ch.broadcast(sm)
    ch.broadcast(um)
    ch.broadcast(m)

    channel_repository.persist(ch)


print("Default")
do_test(connection_factory)
print("Blocking")
do_test(blocking_connection_factory)



