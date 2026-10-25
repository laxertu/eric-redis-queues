from abc import ABC, abstractmethod
from typing import Iterable

from eric_sse.exception import RepositoryError
from eric_sse.interfaces import ListenerRepositoryInterface
from eric_sse.listener import MessageQueueListener
from eric_sse.prefabs import SSEChannelRepository
from eric_sse.repository import KvStorage, ConnectionRepository, KvQueueRepository
from eric_redis_queues import (AbstractRedisQueue, RedisQueue, BlockingRedisQueue,
                               RedisConnection, PREFIX, PREFIX_CONNECTIONS, PREFIX_LISTENERS, PREFIX_CHANNELS, PREFIX_QUEUES,
                               QUEUE_TYPE_DEFAULT, QUEUE_TYPE_BLOCKING)
from eric_sse.connection import DefaultConnectionsFactory
from eric_sse.interfaces import QueueRepositoryInterface
from eric_sse.exception import InvalidListenerException, InvalidConnectionException, ItemNotFound
from redis import Redis
from eric_sse.facade import Facade
from pickle import loads, dumps


def escape_glob(value: str) -> str:
    """Escapes Redis glob-style pattern special characters"""
    return ''.join(f'\\{c}' if c in '*?[]\\' else c for c in value)

class RedisStorage(KvStorage):
    def __init__(self, prefix: str, redis_connection: RedisConnection):
        self._prefix = prefix
        self._client = Redis(host=redis_connection.host, port=redis_connection.port, db=redis_connection.db)

    def _create_object(self, redis_key: str) -> any:

        try:
            raw_result: bytes = self._client.get(redis_key)
            if raw_result is None:
                raise ItemNotFound(redis_key)
            return loads(raw_result)
        except ItemNotFound as e:
            raise e
        except Exception as e:
            raise RepositoryError(e)


    def _scan(self, pattern: str) -> Iterable[any]:
        """Keys deleted while results are iterated are skipped"""
        try:
            for redis_key in self._client.scan_iter(pattern):
                try:
                    yield self._create_object(redis_key.decode())
                except ItemNotFound:
                    continue
        except Exception as e:
            raise RepositoryError(e) from None

    def fetch_by_prefix(self, prefix: str) -> Iterable[any]:
        return self._scan(f"{self._prefix}:{escape_glob(prefix)}*")

    def fetch_all(self) -> Iterable[any]:
        return self._scan(f"{self._prefix}:*")

    def upsert(self, key: str, value: any):
        try:
            self._client.set(f'{self._prefix}:{key}', dumps(value))
        except Exception as e:
            raise RepositoryError(e) from None

    def fetch_one(self, key: str) -> any:
        return self._create_object(f'{self._prefix}:{key}')

    def delete(self, key: str):
        try:
            self._client.delete(f'{self._prefix}:{key}')
        except Exception as e:
            raise RepositoryError(e) from None

class RedisListenerRepository(ListenerRepositoryInterface):
    def __init__(self, redis_connection: RedisConnection):
        self._storage_engine = RedisStorage(prefix=PREFIX_LISTENERS, redis_connection=redis_connection)

    def load(self, connection_id: str) -> MessageQueueListener:
        try:
            return self._storage_engine.fetch_one(connection_id)
        except ItemNotFound as e:
            raise InvalidListenerException(e) from None

    def persist(self, connection_id: str, listener: MessageQueueListener):
        self._storage_engine.upsert(connection_id, listener)

    def delete(self, connection_id: str):
        self._storage_engine.delete(connection_id)

class AbstractRedisConnectionFactory(DefaultConnectionsFactory, ABC):
    def __init__(self, redis_connection: RedisConnection, listener_class: type[MessageQueueListener] = MessageQueueListener):
        self._redis_connection = redis_connection
        super().__init__(listener_class=listener_class, queue_factory=self._create_queue)

    @abstractmethod
    def _create_queue(self) -> AbstractRedisQueue:
        ...

class RedisConnectionFactory(AbstractRedisConnectionFactory):
    def _create_queue(self) -> RedisQueue:
        return RedisQueue(self._redis_connection)

class RedisBlockingQueuesConnectionFactory(AbstractRedisConnectionFactory):
    def _create_queue(self) -> BlockingRedisQueue:
        return BlockingRedisQueue(self._redis_connection)

class RedisQueuesRepository(QueueRepositoryInterface):
    def __init__(self, redis_connection: RedisConnection):
        self._storage_engine = RedisStorage(prefix=PREFIX_QUEUES, redis_connection=redis_connection)

    def load(self, connection_id: str) -> AbstractRedisQueue:

        try:
            queue_data = self._storage_engine.fetch_one(connection_id)
        except ItemNotFound as e:
            raise InvalidConnectionException(e) from None

        queue_type = queue_data.pop('type')

        if queue_type == QUEUE_TYPE_DEFAULT:
            return RedisQueue(**queue_data)
        elif queue_type == QUEUE_TYPE_BLOCKING:
            return BlockingRedisQueue(**queue_data)
        else:
            raise RepositoryError(f"Unknown queue type: {queue_type}")

    def persist(self, connection_id: str, queue: AbstractRedisQueue):
        self._storage_engine.upsert(connection_id, queue.to_dict())

    def delete(self, connection_id: str):
        try:
            queue = self.load(connection_id)
        except InvalidConnectionException:
            return
        queue.clear()
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
            connections_factory=RedisConnectionFactory(redis_connection)
        )

class RedisSSEChannelBlockingQueuesRepository(SSEChannelRepository):
    def __init__(self, redis_connection: RedisConnection):
        super().__init__(
            storage=RedisStorage(redis_connection=redis_connection, prefix=PREFIX_CHANNELS),
            connections_repository=RedisConnectionRepository(redis_connection=redis_connection),
            connections_factory=RedisBlockingQueuesConnectionFactory(redis_connection)
        )


class RedisKvQueueRepository(KvQueueRepository):
    """Queue repository for :class:`~eric_sse.facade.Facade`: deletes queued messages together with the queue"""
    def delete(self, connection_id: str):
        try:
            self.load(connection_id).clear()
        except ItemNotFound:
            return
        super().delete(connection_id)


PREFIX_FACADE = f'{PREFIX}:f'


def create_facade(
        redis_connection: RedisConnection,
        blocking_queues: bool = False,
        listener_class: type[MessageQueueListener] = MessageQueueListener
) -> Facade:
    """Builds a :class:`~eric_sse.facade.Facade` persisting everything in Redis"""
    queue_class = BlockingRedisQueue if blocking_queues else RedisQueue
    return Facade(
        storage=RedisStorage(prefix=PREFIX_FACADE, redis_connection=redis_connection),
        listener_class=listener_class,
        queue_factory=lambda: queue_class(redis_connection),
        queue_repository_class=RedisKvQueueRepository
    )
