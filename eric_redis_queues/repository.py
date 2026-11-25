from eric_sse.builder import ChannelRepositoryBuilder
from eric_sse.exception import ItemNotFound
from eric_sse.interfaces import C
from eric_sse.repository import KvQueueRepository, KvStorage, PrefixedStorage

from eric_redis_queues import RedisConnection, RedisQueue, RedisStorage

__all__ = ['RedisQueueRepository', 'redis_channel_repository_builder']


class RedisQueueRepository(KvQueueRepository[RedisQueue]):
    """
    Creates, persists and loads :class:`~eric_redis_queues.RedisQueue` instances.

    Queues are stored as they are: only their identity (connection data and queue id) is serialised, their messages
    stay in Redis. Deleting a queue deletes its messages too, that would be left in Redis otherwise.

    :param redis_connection: Connection of the queues it creates.
    :param storage: Storage for queues identity, keyed by connection id.
    """

    def __init__(self, redis_connection: RedisConnection, storage: KvStorage):
        super().__init__(storage, queue_factory=lambda: RedisQueue(redis_connection))

    def delete(self, connection_id: str):
        try:
            queue = self.load(connection_id)
        except ItemNotFound:
            return
        queue.purge()
        super().delete(connection_id)


def redis_channel_repository_builder(
        channel_class: type[C],
        redis_connection: RedisConnection | None = None,
        prefix: str | None = None
) -> ChannelRepositoryBuilder[C]:
    """
    Returns a :class:`~eric_sse.builder.ChannelRepositoryBuilder` persisting everything in Redis::

        repository = redis_channel_repository_builder(SSEChannel, RedisConnection(host='localhost')).build()

    It can be further configured before building, e.g. with listeners or error handlers.

    :param channel_class: e.g. :class:`~eric_sse.prefabs.SSEChannel`.
    :param redis_connection: Used by queues, and by the storage of everything else. Defaults to a local Redis,
        database 0.
    :param prefix: Key prefix of the storage, see :class:`~eric_redis_queues.RedisStorage`.
    """
    redis_connection = redis_connection if redis_connection is not None else RedisConnection()
    storage = RedisStorage(redis_connection) if prefix is None else RedisStorage(redis_connection, prefix=prefix)
    return (
        ChannelRepositoryBuilder(channel_class, storage)
        .queues_repository(RedisQueueRepository(redis_connection, PrefixedStorage(storage, 'queue:')))
    )
