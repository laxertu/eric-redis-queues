from eric_redis_queues import (
    AbstractRedisConnectionRepository, RedisNonBlockingQueuesRepository, RedisBlockingQueuesRepository,
    RedisSSEChannelRepository
)
from eric_sse.message import SignedMessage, UniqueMessage, Message
from eric_sse.prefabs import SSEChannel

repo_1 = RedisNonBlockingQueuesRepository()
repo_2 = RedisBlockingQueuesRepository()


def do_test(r: AbstractRedisConnectionRepository):
    ch = SSEChannel()

    sm = SignedMessage(sender_id='admin', msg_type='test', msg_payload='hi there')
    um = UniqueMessage(message_id='mgs_id0001', sender_id='administrator',
                       message=Message(msg_type='test2', msg_payload={'a': 1}))
    m = Message(msg_type='testsimple', msg_payload='hi, simple')
    l = ch.add_listener()
    print("")
    print(f'python run.py {ch.id} {l.id}')
    print("")
    ch.broadcast(sm)
    ch.broadcast(um)
    ch.broadcast(m)

    repo_persist = RedisSSEChannelRepository(connection_repository=r)
    repo_persist.persist(ch)

print("Default")
do_test(repo_1)
print("Blocking")
do_test(repo_2)

