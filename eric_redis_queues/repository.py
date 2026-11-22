from typing import Callable

from eric_sse.builder import ChannelRepositoryBuilder
from eric_sse.exception import ItemNotFound
from eric_sse.interfaces import C
from eric_sse.queues import Queue
from eric_sse.repository import KvQueueRepository, KvStorage, PrefixedStorage

from eric_redis_queues import RedisConnection, RedisQueue, RedisStorage

__all__ = ['RedisStorage', 'RedisQueueRepository', 'redis_channel_repository_builder']


class RedisQueueRepository(KvQueueRepository):
    """
    :class:`~eric_sse.repository.KvQueueRepository` that also deletes the messages of the queues it deletes.

    Queues keep their messages in Redis, outside the storage: without this, deleting a connection would leave
    its messages behind. Queues having a ``purge()`` method, as :class:`~eric_redis_queues.RedisQueue` does, are
    purged.

    :param storage: Storage for queues identity.
    :param queue_factory: Called once per connection to create its queue.
    """

    def __init__(self, storage: KvStorage, queue_factory: Callable[[], Queue]):
        super().__init__(storage, queue_factory=queue_factory)

    def delete(self, connection_id: str):
        try:
            queue = self.load(connection_id)
        except ItemNotFound:
            return
        purge = getattr(queue, 'purge', None)
        if callable(purge):
            purge()
        super().delete(connection_id)


def redis_channel_repository_builder(
        channel_class: type[C],
        redis_connection: RedisConnection | None = None,
        queue_factory: Callable[[], Queue] | None = None,
        prefix: str | None = None
) -> ChannelRepositoryBuilder[C]:
    """
    Returns a :class:`~eric_sse.builder.ChannelRepositoryBuilder` persisting everything in Redis::

        repository = redis_channel_repository_builder(SSEChannel, RedisConnection()).build()

    It can be further configured before building, e.g. with listeners or error handlers.

    :param channel_class: e.g. :class:`~eric_sse.prefabs.SSEChannel`.
    :param redis_connection: Defaults to a local Redis.
    :param queue_factory: Creates connections queues. Defaults to :class:`~eric_redis_queues.RedisQueue`.
    :param prefix: Key prefix of the storage, see :class:`~eric_redis_queues.RedisStorage`.
    """
    redis_connection = redis_connection if redis_connection is not None else RedisConnection()
    storage = RedisStorage(redis_connection) if prefix is None else RedisStorage(redis_connection, prefix=prefix)
    if queue_factory is None:
        queue_factory = lambda: RedisQueue(redis_connection)  # noqa: E731

    return (
        ChannelRepositoryBuilder(channel_class, storage)
        .queues_repository(RedisQueueRepository(PrefixedStorage(storage, 'queue:'), queue_factory=queue_factory))
    )
