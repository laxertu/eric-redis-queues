from eric_redis_queues import RedisConnectionsRepository, RedisSSEChannelRepository
from eric_sse.message import SignedMessage, UniqueMessage, Message
from eric_sse.prefabs import SSEChannel
repo = RedisConnectionsRepository()

ch = SSEChannel(connections_repository=RedisConnectionsRepository())

sm = SignedMessage(sender_id='admin', msg_type='test', msg_payload='hi there')
um = UniqueMessage(message_id='mgs_id0001', sender_id='administrator', message=Message(msg_type='test2', msg_payload={'a': 1}))
m = Message(msg_type='testsimple', msg_payload='hi, simple')
l = ch.add_listener()
print(f'python run.py {ch.id} {l.id}')
ch.broadcast(sm)
ch.broadcast(um)
ch.broadcast(m)

repo_persist = RedisSSEChannelRepository()
repo_persist.persist(ch)
