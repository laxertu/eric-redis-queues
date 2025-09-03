from eric_sse.message import SignedMessage, UniqueMessage, Message

from eric_redis_queues import RedisConnection
from eric_redis_queues.repository import RedisBlockingQueuesConnectionFactory, RedisSSEChannelRepository
from eric_sse.prefabs import SSEChannel, SSEChannelRepository

redis_connection = RedisConnection()
channel_repository = RedisSSEChannelRepository(redis_connection=redis_connection)

def do_test(repo_persist: SSEChannelRepository):
    connection_factory = RedisBlockingQueuesConnectionFactory(redis_connection)
    ch = SSEChannel(connections_factory=connection_factory)

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

    repo_persist.persist(ch)

do_test(channel_repository)


#print("Default")
#do_test(channel_repository)
#print("Blocking")
#do_test(blocking_repository)


