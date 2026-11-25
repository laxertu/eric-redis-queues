"""
Redis support for eric-sse: :class:`RedisStorage` persists channels, connections, listeners and queues,
:class:`RedisQueue` keeps messages. See :func:`eric_redis_queues.repository.redis_channel_repository_builder`.
"""
import asyncio
import threading
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from pickle import dumps, loads
from typing import Any, Iterable

from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from eric_sse import generate_uuid, get_logger
from eric_sse.exception import ItemNotFound, NoMessagesException, RepositoryError
from eric_sse.message import MessageContract
from eric_sse.queues import Queue
from eric_sse.repository import KvStorage

logger = get_logger()

PREFIX = 'eric-redis-queues'
PREFIX_STORAGE = f'{PREFIX}:kv:'
"""Default key prefix of :class:`RedisStorage`."""
PREFIX_MESSAGES = f'{PREFIX}:m'
"""Key prefix of :class:`RedisQueue` message lists."""


@dataclass(frozen=True)
class RedisConnection:
    host: str = '127.0.0.1'
    port: int = 6379
    db: int = 0

    def create_client(self) -> Redis:
        return Redis(host=self.host, port=self.port, db=self.db)

    def create_async_client(self) -> AsyncRedis:
        return AsyncRedis(host=self.host, port=self.port, db=self.db)


@contextmanager
def _repository_errors():
    try:
        yield
    except Exception as e:
        raise RepositoryError(e) from None


def _escape_glob(value: str) -> str:
    return ''.join(f'\\{c}' if c in '\\*?[]' else c for c in value)


_lock = threading.Lock()
_clients: dict[RedisConnection, Redis] = {}
_async_clients: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()  # Async clients belong to one event loop


def _shared_client(redis_connection: RedisConnection) -> Redis:
    with _lock:
        if redis_connection not in _clients:
            _clients[redis_connection] = redis_connection.create_client()
        return _clients[redis_connection]


def _shared_async_client(redis_connection: RedisConnection) -> AsyncRedis:
    clients = _async_clients.setdefault(asyncio.get_running_loop(), {})
    if redis_connection not in clients:
        clients[redis_connection] = redis_connection.create_async_client()
    return clients[redis_connection]


class RedisStorage(KvStorage):
    """
    :class:`~eric_sse.repository.KvStorage` backed by Redis. Values are pickled.

    :param redis_connection: Defaults to a local Redis, database 0. Shares the client of queues with equal connection data.
    :param prefix: Prepended to every key. Prefixes of storages sharing a database must not be prefixes of each other.
    """

    def __init__(self, redis_connection: RedisConnection | None = None, prefix: str = PREFIX_STORAGE):
        self.__client = _shared_client(redis_connection or RedisConnection())
        self.__prefix = prefix

    @property
    def prefix(self) -> str:
        return self.__prefix

    def fetch_by_prefix(self, prefix: str) -> Iterable[Any]:
        # Fetched before returning, so callers can delete keys while iterating
        with _repository_errors():
            keys = list(self.__client.scan_iter(match=f'{_escape_glob(self.__prefix + prefix)}*', count=1000))
            values = self.__client.mget(keys) if keys else []
        return [loads(value) for value in values if value is not None]  # None: deleted after SCAN

    def upsert(self, key: str, value: Any):
        with _repository_errors():
            self.__client.set(self.__prefix + key, dumps(value))

    def fetch_one(self, key: str) -> Any:
        with _repository_errors():
            value = self.__client.get(self.__prefix + key)
        if value is None:
            raise ItemNotFound(key=key)
        return loads(value)

    def delete(self, key: str):
        with _repository_errors():
            self.__client.delete(self.__prefix + key)


class RedisQueue(Queue):
    """
    Durable queue keeping pickled messages in a Redis list. Pickling it saves only its connection data and id.

    :meth:`pop` without timeout returns immediately, with a timeout it waits with
    `BLPOP <https://redis.io/docs/latest/commands/blpop/>`_. :meth:`wait_pop` runs BLPOP on an async client, so it
    holds no thread, but holds a Redis connection while waiting. Queues with equal connection data share one client
    per event loop.

    :param redis_connection: Defaults to a local Redis, database 0.
    :param queue_id: Defaults to a new uuid.
    """

    def __init__(self, redis_connection: RedisConnection | None = None, queue_id: str | None = None):
        self.__redis_connection = redis_connection or RedisConnection()
        self.__queue_id = queue_id or generate_uuid()
        self.__client = _shared_client(self.__redis_connection)

    def __getstate__(self) -> dict:
        return {'redis_connection': self.__redis_connection, 'queue_id': self.__queue_id}

    def __setstate__(self, state: dict) -> None:
        self.__init__(**state)

    @property
    def queue_id(self) -> str:
        return self.__queue_id

    @property
    def redis_connection(self) -> RedisConnection:
        return self.__redis_connection

    @property
    def _key(self) -> str:
        return f'{PREFIX_MESSAGES}:{self.__queue_id}'

    def push(self, message: MessageContract) -> None:
        with _repository_errors():
            self.__client.rpush(self._key, dumps(message))

    def pop(self, timeout: float = 0) -> Any:
        with _repository_errors():
            # BLPOP waits forever with a 0 timeout
            popped = self.__client.blpop([self._key], timeout=timeout) if timeout > 0 else self.__client.lpop(self._key)
        return self.__loads(popped)

    async def wait_pop(self, timeout: float) -> Any:
        if timeout <= 0:
            return self.pop()
        # A running BLPOP can't be interrupted without losing what it pops: on cancellation it ends by itself
        popping = asyncio.ensure_future(_shared_async_client(self.__redis_connection).blpop([self._key], timeout=timeout))
        try:
            with _repository_errors():
                popped = await asyncio.shield(popping)
        except asyncio.CancelledError:
            popping.add_done_callback(self.__put_back)
            raise
        return self.__loads(popped)

    @staticmethod
    def __loads(popped: bytes | list | None) -> Any:
        if popped is None:
            raise NoMessagesException
        return loads(popped[1] if isinstance(popped, (list, tuple)) else popped)

    def __put_back(self, popping: asyncio.Future) -> None:
        if popping.cancelled() or popping.exception() or popping.result() is None:
            return
        try:
            self.__client.lpush(self._key, popping.result()[1])
        except Exception as e:
            logger.error(f'Message of queue {self.__queue_id} lost after a cancelled wait: {e!r}')

    def purge(self) -> None:
        """Deletes all its messages."""
        with _repository_errors():
            self.__client.delete(self._key)
