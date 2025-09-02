from abc import ABC
from typing import Iterable

from eric_sse.interfaces import ListenerRepositoryInterface
from eric_sse.listener import MessageQueueListener
from eric_sse.prefabs import SSEChannelRepository
from eric_sse.repository import KvStorage, ConnectionRepository
from eric_redis_queues import (AbstractRedisQueue, RedisQueue, BlockingRedisQueue,
                               RedisConnection, PREFIX_CONNECTIONS, PREFIX_LISTENERS, PREFIX_CHANNELS, PREFIX_QUEUES)
from eric_sse.connection import ConnectionsFactory, Connection
from eric_sse.interfaces import QueueRepositoryInterface
from redis import Redis
from pickle import loads, dumps


class RedisStorage(KvStorage):
    def __init__(self, prefix: str, redis_connection: RedisConnection):
        """
        self.host: str = redis_connection.host
        self.port: int = redis_connection.port
        self.db: int = redis_connection.db
        """
        self._prefix = prefix
        self._client = Redis(host=redis_connection.host, port=redis_connection.port, db=redis_connection.db)


    def fetch_by_prefix(self, prefix: str) -> Iterable[any]:
        for redis_key in self._client.scan_iter(f"{self._prefix}:{prefix}:*"):
            yield loads(self._client.get(redis_key.decode()))

    def fetch_all(self) -> Iterable[any]:
        for redis_key in self._client.scan_iter(f"{self._prefix}:*"):
            yield loads(self._client.get(redis_key.decode()))

    def upsert(self, key: str, value: any):
        self._client.set(f'{self._prefix}:{key}', dumps(value))

    def fetch_one(self, key: str) -> any:
        return loads(self._client.get(f'{self._prefix}:{key}'))

    def delete(self, key: str):
        self._client.delete(f'{self._prefix}:{key}')

class RedisListenerRepository(ListenerRepositoryInterface):
    def __init__(self, redis_connection: RedisConnection):
        self._storage_engine = RedisStorage(prefix=PREFIX_LISTENERS, redis_connection=redis_connection)

    def load(self, connection_id: str) -> MessageQueueListener:
        return self._storage_engine.fetch_one(connection_id)

    def persist(self, connection_id: str, listener: MessageQueueListener):
        self._storage_engine.upsert(connection_id, listener)

    def delete(self, connection_id: str):
        self._storage_engine.delete(connection_id)

class AbstractRedisConnectionFactory(ConnectionsFactory, ABC):
    def __init__(self, redis_connection: RedisConnection):
        self._redis_connection = redis_connection
        self._storage_engine: RedisStorage = RedisStorage(
            prefix=PREFIX_CONNECTIONS, redis_connection=self._redis_connection
        )

class RedisConnectionFactory(AbstractRedisConnectionFactory):
    def create(self, listener: MessageQueueListener | None = None) -> Connection:
        if listener is None:
            listener = MessageQueueListener()
        return Connection(
            listener=listener,
            queue=RedisQueue(self._redis_connection, queue_id=listener.id)
        )

class RedisBlockingQueuesConnectionFactory(AbstractRedisConnectionFactory):

    def create(self, listener: MessageQueueListener | None = None) -> Connection:
        if listener is None:
            listener = MessageQueueListener()
        return Connection(
            listener=listener,
            queue=BlockingRedisQueue(self._redis_connection, queue_id=listener.id)
        )

class RedisQueuesRepository(QueueRepositoryInterface):
    def __init__(self, redis_connection: RedisConnection):
        self._storage_engine = RedisStorage(prefix=PREFIX_QUEUES, redis_connection=redis_connection)

    def load(self, connection_id: str) -> AbstractRedisQueue:
        return self._storage_engine.fetch_one(connection_id)

    def persist(self, connection_id: str, queue: AbstractRedisQueue):
        self._storage_engine.upsert(connection_id, queue.to_dict())

    def delete(self, connection_id: str):
        self._storage_engine.delete(connection_id)

class RedisConnectionRepository(ConnectionRepository):
    def __init__(self, redis_connection: RedisConnection):
        super().__init__(
            storage=RedisStorage(prefix=PREFIX_CONNECTIONS, redis_connection=redis_connection),
            listeners_repository=RedisListenerRepository(redis_connection),
            queues_repository=RedisQueuesRepository(redis_connection)
        )

class RedisSSEChannelRepository(SSEChannelRepository):
    def __init__(self, redis_connection: RedisConnection):
        super().__init__(
            storage=RedisStorage(redis_connection=redis_connection, prefix=PREFIX_CHANNELS),
            connections_repository=RedisConnectionRepository(redis_connection=redis_connection),
            connections_factory=RedisBlockingQueuesConnectionFactory(redis_connection)
        )