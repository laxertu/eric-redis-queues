"""
Redis support for eric-sse.

* :class:`RedisStorage`: a :class:`~eric_sse.repository.KvStorage`, to persist channels, connections, listeners and queues;
* :class:`RedisQueue`: a durable :class:`~eric_sse.queues.Queue`, whose messages live in a Redis list.

See :func:`eric_redis_queues.repository.redis_channel_repository_builder` to wire them together.
"""
from dataclasses import dataclass
from pickle import dumps, loads
from typing import Any, Iterable

from redis import Redis

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
"""Key prefix of the lists holding :class:`RedisQueue` messages."""

_GLOB_SPECIAL_CHARS = '\\*?[]'


@dataclass(frozen=True)
class RedisConnection:
    host: str = '127.0.0.1'
    port: int = 6379
    db: int = 0

    def create_client(self) -> Redis:
        return Redis(host=self.host, port=self.port, db=self.db)


def _escape_glob(value: str) -> str:
    return ''.join(f'\\{c}' if c in _GLOB_SPECIAL_CHARS else c for c in value)


class RedisStorage(KvStorage):
    """
    :class:`~eric_sse.repository.KvStorage` backed by Redis. Values are pickled.

    It can be pickled itself: only its connection data and prefix are.

    :param redis_connection: Defaults to a local Redis.
    :param prefix: Prepended to every key. Storages sharing a Redis database must have prefixes that are not
        prefixes of each other.
    """

    def __init__(self, redis_connection: RedisConnection | None = None, prefix: str = PREFIX_STORAGE):
        self.__redis_connection = redis_connection if redis_connection is not None else RedisConnection()
        self.__prefix = prefix
        self._client = self.__redis_connection.create_client()

    def __getstate__(self) -> dict:
        return {'redis_connection': self.__redis_connection, 'prefix': self.__prefix}

    def __setstate__(self, state: dict) -> None:
        self.__init__(**state)

    @property
    def prefix(self) -> str:
        return self.__prefix

    def fetch_by_prefix(self, prefix: str) -> Iterable[Any]:
        # Keys and values are fetched before yielding, so callers can delete keys while iterating
        try:
            keys = list(self._client.scan_iter(match=f'{_escape_glob(self.__prefix + prefix)}*', count=1000))
            raw_values = self._client.mget(keys) if keys else []
        except Exception as e:
            raise RepositoryError(e) from None
        # A key deleted between SCAN and MGET is skipped
        return [loads(raw) for raw in raw_values if raw is not None]

    def upsert(self, key: str, value: Any):
        try:
            self._client.set(f'{self.__prefix}{key}', dumps(value))
        except Exception as e:
            raise RepositoryError(e) from None

    def fetch_one(self, key: str) -> Any:
        try:
            raw = self._client.get(f'{self.__prefix}{key}')
        except Exception as e:
            raise RepositoryError(e) from None
        if raw is None:
            raise ItemNotFound(key=key)
        return loads(raw)

    def delete(self, key: str):
        try:
            self._client.delete(f'{self.__prefix}{key}')
        except Exception as e:
            raise RepositoryError(e) from None


class RedisQueue(Queue):
    """
    Durable queue: messages are pickled and kept in a Redis list, so several processes can share it.

    When pickled, e.g. by a queue repository, only its identity (connection data and queue id) is saved:
    its messages stay in Redis.

    :meth:`pop` without timeout returns immediately, as eric-sse requires. With a timeout it waits for a message,
    relying on `BLPOP <https://redis.io/docs/latest/commands/blpop/>`_, so it doesn't poll. This replaces
    ``BlockingRedisQueue`` of previous versions: callers choose whether to wait, e.g. with
    :meth:`~eric_sse.entities.AbstractChannel.wait_next` or ``queue.pop(timeout=...)``.
    :meth:`~eric_sse.queues.Queue.wait_pop` is inherited: it runs :meth:`pop` in a worker thread.

    :param redis_connection: Defaults to a local Redis.
    :param queue_id: Identifies the Redis list. Defaults to a new uuid.
    """

    def __init__(self, redis_connection: RedisConnection | None = None, queue_id: str | None = None):
        self.__redis_connection = redis_connection if redis_connection is not None else RedisConnection()
        self.__queue_id = queue_id if queue_id is not None else generate_uuid()
        self._client = self.__redis_connection.create_client()

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

    def pop(self, timeout: float = 0) -> Any:
        try:
            if timeout > 0:
                # BLPOP blocks forever with a 0 timeout, so it's only used with a positive one
                result = self._client.blpop([self._key], timeout=timeout)
                raw_value = result[1] if result is not None else None
            else:
                raw_value = self._client.lpop(self._key)
        except Exception as e:
            raise RepositoryError(e) from None

        if raw_value is None:
            raise NoMessagesException
        return loads(raw_value)

    def push(self, message: MessageContract) -> None:
        try:
            self._client.rpush(self._key, dumps(message))
        except Exception as e:
            raise RepositoryError(e) from None

    def purge(self) -> None:
        """Deletes all its messages."""
        try:
            self._client.delete(self._key)
        except Exception as e:
            raise RepositoryError(e) from None

