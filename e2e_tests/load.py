from eric_redis_queues.prefabs import RedisQueuesRepository, BlockingRedisQueuesRepository, RedisStorageEngine
from eric_redis_queues import RedisConnection
from eric_sse.message import SignedMessage, UniqueMessage, Message
from eric_sse.prefabs import SSEChannel

from eric_sse.serializable import ChannelRepository, ConnectionRepository, ListenerRepository


storage_engine_1 = RedisStorageEngine(kv_prefix='nonblocking', redis_connection=RedisConnection())
repo_1 = RedisQueuesRepository(storage_engine=storage_engine_1)

storage_engine_2 = RedisStorageEngine(kv_prefix='blocking', redis_connection=RedisConnection())
repo_2 = BlockingRedisQueuesRepository(storage_engine=storage_engine_2)


channel_repository_1 = ChannelRepository(
    connection_repository=ConnectionRepository(
        listeners_repository=ListenerRepository(RedisStorageEngine(kv_prefix='l', redis_connection=RedisConnection())),
        queues_repository=RedisQueuesRepository(storage_engine=storage_engine_1),
        storage_engine=storage_engine_1
    ),
    storage_engine=storage_engine_1
)

channel_repository_2 = ChannelRepository(
    connection_repository=ConnectionRepository(
        listeners_repository=ListenerRepository(RedisStorageEngine(kv_prefix='l', redis_connection=RedisConnection())),
        queues_repository=RedisQueuesRepository(storage_engine=storage_engine_2),
        storage_engine=storage_engine_1
    ),
    storage_engine=storage_engine_2
)

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

channel_repository_1.persist(ch)
channel_repository_2.persist(ch)
