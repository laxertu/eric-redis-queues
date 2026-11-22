from redis import Redis

from eric_sse.builder import ChannelRepositoryBuilder
from eric_sse.interfaces import C, QueueRepositoryInterface
from eric_sse.exception import ItemNotFound
from eric_sse.repository import KvStorage, PrefixedStorage

from eric_redis_queues import RedisQueue, RedisStorage

__all__ = ['RedisStorage', 'RedisQueueRepository', 'redis_channel_repository_builder']


class RedisQueueRepository(QueueRepositoryInterface[RedisQueue]):
    """
    Creates, persists and loads :class:`~eric_redis_queues.RedisQueue` instances.

    Only queue ids are stored: loaded queues get **client**. Deleting a queue deletes its messages too.

    :param client: Given to the queues it creates and loads, see :class:`~eric_redis_queues.RedisQueue`.
    :param storage: Storage for queue ids, keyed by connection id.
    """

    def __init__(self, client: Redis, storage: KvStorage):
        self.__client = client
        self.__storage = storage

    def create(self) -> RedisQueue:
        return RedisQueue(self.__client)

    def load(self, connection_id: str) -> RedisQueue:
        return RedisQueue(self.__client, queue_id=self.__storage.fetch_one(connection_id)['queue_id'])

    def persist(self, connection_id: str, queue: RedisQueue):
        self.__storage.upsert(connection_id, {'queue_id': queue.queue_id})

    def delete(self, connection_id: str):
        try:
            queue = self.load(connection_id)
        except ItemNotFound:
            return
        queue.purge()
        self.__storage.delete(connection_id)


def redis_channel_repository_builder(
        channel_class: type[C],
        client: Redis,
        prefix: str | None = None
) -> ChannelRepositoryBuilder[C]:
    """
    Returns a :class:`~eric_sse.builder.ChannelRepositoryBuilder` persisting everything in Redis::

        repository = redis_channel_repository_builder(SSEChannel, Redis(host='localhost')).build()

    It can be further configured before building, e.g. with listeners or error handlers.

    :param channel_class: e.g. :class:`~eric_sse.prefabs.SSEChannel`.
    :param client: Must not decode responses (``decode_responses=False``, the default).
    :param prefix: Key prefix of the storage, see :class:`~eric_redis_queues.RedisStorage`.
    """
    storage = RedisStorage(client) if prefix is None else RedisStorage(client, prefix=prefix)
    return (
        ChannelRepositoryBuilder(channel_class, storage)
        .queues_repository(RedisQueueRepository(client, PrefixedStorage(storage, 'queue:')))
    )
