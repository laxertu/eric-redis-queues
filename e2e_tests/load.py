from eric_redis_queues.prefabs import RedisSSENonBlockingChannelApplication, RedisConnection
from eric_sse.prefabs import SSEChannel

# channels are saved or creation. Subsequent load calls return new instances with same properties
app = RedisSSENonBlockingChannelApplication(RedisConnection())
channel = app.create_channel(retry_timeout_millis=987)

app2 = RedisSSENonBlockingChannelApplication(RedisConnection())
channel2: SSEChannel = app2.channel_repository.load_one(channel_id=channel.id)

assert id(channel) != id(channel2)
assert channel.id == channel2.id
assert channel2.retry_timeout_milliseconds == channel.retry_timeout_milliseconds




"""
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

    repo_persist = ChannelRepository(RedisStorageEngine('e2e-tests-channels'))
    repo_persist.persist(ch)

print("Default")
do_test(repo_1)
print("Blocking")
do_test(repo_2)
"""

