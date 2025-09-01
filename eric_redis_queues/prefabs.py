from abc import ABC
from pickle import loads, dumps
from typing import Iterable

from eric_sse.interfaces import ListenerRepositoryInterface, QueueRepositoryInterface
from eric_sse.listener import MessageQueueListener
from eric_sse.queues import Queue
from redis import Redis

from eric_redis_queues import RedisQueue, BlockingRedisQueue, AbstractRedisQueue
from eric_sse.repository import AbstractChannelRepository, AbstractConnectionRepository

class RedisStorageEngine:
    def __init__(self, prefix: str, host='127.0.0.1', port=6379, db=0):
        self.host: str = host
        self.port: int = port
        self.db: int = db
        self._prefix = prefix
        self._client = Redis(host=host, port=port, db=db)


    def fetch_by_prefix(self, prefix: str) -> Iterable[any]:
        for redis_key in self._client.scan_iter(f"{self._prefix}:{prefix}:*"):
            key = redis_key.decode()
            yield self.fetch_one(key)

    def fetch_all(self) -> Iterable[any]:
        for redis_key in self._client.scan_iter(f"{self._prefix}:*"):
            yield self.fetch_one(redis_key.decode())

    def upsert(self, key: str, value: any):
        self._client.set(f'{self._prefix}:{key}', dumps(value))

    def fetch_one(self, key: str) -> any:
        return loads(self._client.get(f'{self._prefix}:{key}'))

    def delete(self, key: str):
        self._client.delete(f'{self._prefix}:{key}')


class RedisListenerRepository(ListenerRepositoryInterface):
    def __init__(self,storage_engine: RedisStorageEngine):
        self._storage_engine: RedisStorageEngine = storage_engine

    def load(self, connection_id: str) -> MessageQueueListener:
        return self._storage_engine.fetch_one(connection_id)

    def persist(self, connection_id: str, listener: MessageQueueListener):
        self._storage_engine.upsert(connection_id, listener)

    def delete(self, connection_id: str):
        self._storage_engine.delete(connection_id)


class AbstractRedisQueueRepository(QueueRepositoryInterface, ABC):
    def __init__(self,storage_engine: RedisStorageEngine):
        self._storage_engine: RedisStorageEngine = storage_engine

    def persist(self, connection_id: str, queue: AbstractRedisQueue):
        self._storage_engine.upsert(connection_id, queue.to_dict())

    def delete(self, connection_id: str):
        self._storage_engine.delete(connection_id)


class RedisNonBlockingQueuesRepository(AbstractRedisQueueRepository):

    def load(self, connection_id: str) -> Queue:
        return RedisQueue(**self._storage_engine.fetch_one(connection_id))

class RedisBlockingQueuesRepository(AbstractRedisQueueRepository):

    def load(self, connection_id: str) -> Queue:
        return BlockingRedisQueue(**self._storage_engine.fetch_one(connection_id))


class RedisNonBlockingConnectionRepository(AbstractConnectionRepository):

    def _create_listener(self, listener_data: dict) -> MessageQueueListener:
        return MessageQueueListener(**listener_data)

    def _create_queue(self, queue_data: dict) -> RedisQueue:
        return RedisQueue(**queue_data)

class RedisBlockingConnectionRepository(AbstractConnectionRepository):

    def _create_listener(self, listener_data: dict) -> any:
        return MessageQueueListener(**listener_data)

    def _create_queue(self, queue_data: dict) -> BlockingRedisQueue:
        return BlockingRedisQueue(**queue_data)