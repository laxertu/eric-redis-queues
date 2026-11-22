"""
Producer side of a two-process check: persists a channel with one connection, then dispatches messages.

Usage: python -m e2e_tests.load, then run the printed command.
"""
import os

from eric_sse.message import Message, SignedMessage
from eric_sse.prefabs import SSEChannel
from redis import Redis

from eric_redis_queues.repository import redis_channel_repository_builder

redis_client = Redis(
    host=os.environ.get('REDIS_HOST', '127.0.0.1'),
    port=int(os.environ.get('REDIS_PORT', '6379')),
    db=int(os.environ.get('REDIS_DB', '0')),
)


def build_repository():
    return redis_channel_repository_builder(SSEChannel, redis_client).build()


def load() -> str:
    repository = build_repository()
    channel = repository.create({})
    connection = channel.add_connection()
    repository.persist(channel)

    # Queues write messages to Redis themselves: no persist needed after dispatching
    channel.broadcast(SignedMessage(sender_id='admin', msg_type='test', msg_payload='hi there'))
    channel.broadcast(Message(msg_type='test2', msg_payload={'a': 1}, msg_id='msg_id0001'))
    channel.broadcast(Message(msg_type='testsimple', msg_payload='hi, simple'))

    return f'python -m e2e_tests.run {channel.id} {connection.id}'


if __name__ == '__main__':
    print(load())
