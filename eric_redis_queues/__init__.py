"""
Redis support for eric-sse.

* :class:`RedisStorage`: a :class:`~eric_sse.repository.KvStorage`, to persist channels, connections, listeners and queues;
* :class:`RedisQueue`: a durable :class:`~eric_sse.queues.Queue`, whose messages live in a Redis list.

:class:`RedisQueue` is described by a :class:`RedisConnection` (host, port and database), so it can be pickled.
:class:`RedisStorage` takes a ``redis.Redis`` client. See
:func:`eric_redis_queues.repository.redis_channel_repository_builder` to wire them together.
"""
import asyncio
import os
import threading
import time
from dataclasses import dataclass
from pickle import dumps, loads
from typing import Any, Callable, Iterable

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
PREFIX_WAKE = f'{PREFIX}:wake'
"""Prefix of the Pub/Sub channels notifying pushes to :class:`RedisQueue` instances, one per database."""
NOTIFIER_CLIENT_NAME = f'{PREFIX}:notifier'
"""Name of the Redis connections receiving push notifications, one per process and :class:`RedisConnection`."""

_GLOB_SPECIAL_CHARS = '\\*?[]'


@dataclass(frozen=True)
class RedisConnection:
    """Where a :class:`RedisQueue` keeps its messages."""
    host: str = '127.0.0.1'
    port: int = 6379
    db: int = 0

    def create_client(self) -> Redis:
        """Returns a new client. :class:`RedisQueue` instances share one client per connection instead."""
        return Redis(host=self.host, port=self.port, db=self.db)


_clients: dict[RedisConnection, Redis] = {}
_clients_lock = threading.Lock()


def _shared_client(redis_connection: RedisConnection) -> Redis:
    """One client, so one connection pool, per connection data: queues are many, one per eric-sse connection."""
    with _clients_lock:
        client = _clients.get(redis_connection)
        if client is None:
            client = _clients[redis_connection] = redis_connection.create_client()
        return client


def _check_client(client: Redis) -> Redis:
    """Values are pickled bytes: a client decoding responses to strings would corrupt them."""
    if client.get_connection_kwargs().get('decode_responses'):
        raise ValueError('The Redis client must not decode responses (decode_responses=False)')
    return client


def _escape_glob(value: str) -> str:
    return ''.join(f'\\{c}' if c in _GLOB_SPECIAL_CHARS else c for c in value)


class RedisStorage(KvStorage):
    """
    :class:`~eric_sse.repository.KvStorage` backed by Redis. Values are pickled.

    :param client: Must not decode responses (``decode_responses=False``, the default).
    :param prefix: Prepended to every key. Storages sharing a Redis database must have prefixes that are not
        prefixes of each other.
    """

    def __init__(self, client: Redis, prefix: str = PREFIX_STORAGE):
        self.__client = _check_client(client)
        self.__prefix = prefix

    @property
    def prefix(self) -> str:
        return self.__prefix

    def fetch_by_prefix(self, prefix: str) -> Iterable[Any]:
        # Keys and values are fetched before yielding, so callers can delete keys while iterating
        try:
            keys = list(self.__client.scan_iter(match=f'{_escape_glob(self.__prefix + prefix)}*', count=1000))
            raw_values = self.__client.mget(keys) if keys else []
        except Exception as e:
            raise RepositoryError(e) from None
        # A key deleted between SCAN and MGET is skipped
        return [loads(raw) for raw in raw_values if raw is not None]

    def upsert(self, key: str, value: Any):
        try:
            self.__client.set(f'{self.__prefix}{key}', dumps(value))
        except Exception as e:
            raise RepositoryError(e) from None

    def fetch_one(self, key: str) -> Any:
        try:
            raw = self.__client.get(f'{self.__prefix}{key}')
        except Exception as e:
            raise RepositoryError(e) from None
        if raw is None:
            raise ItemNotFound(key=key)
        return loads(raw)

    def delete(self, key: str):
        try:
            self.__client.delete(f'{self.__prefix}{key}')
        except Exception as e:
            raise RepositoryError(e) from None


def _wake_channel(redis_connection: RedisConnection) -> str:
    # Pub/Sub channels are shared by all databases of a server, so the database is part of the name
    return f'{PREFIX_WAKE}:{redis_connection.db}'


class _Notifier:
    """
    Receives push notifications of a :class:`RedisConnection` and wakes the local waiters of the queues they name.

    One per process and connection: a thread holding one Pub/Sub connection, whatever the number of waiters.
    Waiters always check their queue after registering, and every waiter is woken when the subscription is
    (re)established, so a notification lost while disconnected only causes a check, never a lost message.
    """

    def __init__(self, redis_connection: RedisConnection):
        self.__redis_connection = redis_connection
        self.__waiters: dict[str, list[Callable[[], None]]] = {}
        self.__lock = threading.Lock()
        self.pid = os.getpid()
        threading.Thread(target=self.__run, name=NOTIFIER_CLIENT_NAME, daemon=True).start()

    def register(self, queue_id: str, wake: Callable[[], None]) -> None:
        with self.__lock:
            self.__waiters.setdefault(queue_id, []).append(wake)

    def unregister(self, queue_id: str, wake: Callable[[], None]) -> None:
        with self.__lock:
            waiters = self.__waiters.get(queue_id, [])
            if wake in waiters:
                waiters.remove(wake)
            if not waiters:
                self.__waiters.pop(queue_id, None)

    def __wake(self, queue_id: str | None) -> None:
        """Wakes waiters of **queue_id**, or all of them."""
        with self.__lock:
            if queue_id is None:
                to_wake = [wake for waiters in self.__waiters.values() for wake in waiters]
            else:
                to_wake = list(self.__waiters.get(queue_id, ()))
        for wake in to_wake:
            wake()

    def __run(self) -> None:
        client = Redis(
            host=self.__redis_connection.host,
            port=self.__redis_connection.port,
            db=self.__redis_connection.db,
            client_name=NOTIFIER_CLIENT_NAME,
        )
        pubsub = None
        backoff = 0.1
        while True:
            try:
                if pubsub is None:
                    pubsub = client.pubsub()
                    pubsub.subscribe(_wake_channel(self.__redis_connection))
                message = pubsub.get_message(timeout=1.0)
                backoff = 0.1
                if message is None:
                    continue
                if message['type'] == 'subscribe':
                    # Also received after an automatic reconnection: notifications may have been missed
                    self.__wake(None)
                elif message['type'] == 'message':
                    self.__wake(message['data'].decode())
            except Exception as e:
                logger.warning(f'Push notifications interrupted, retrying in {backoff}s: {e!r}')
                try:
                    if pubsub is not None:
                        pubsub.close()
                except Exception:
                    pass
                pubsub = None
                self.__wake(None)
                time.sleep(backoff)
                backoff = min(backoff * 2, 5.0)


_notifiers: dict[RedisConnection, _Notifier] = {}
_notifiers_lock = threading.Lock()


def _notifier(redis_connection: RedisConnection) -> _Notifier:
    with _notifiers_lock:
        notifier = _notifiers.get(redis_connection)
        if notifier is None or notifier.pid != os.getpid():  # Threads don't survive a fork
            notifier = _notifiers[redis_connection] = _Notifier(redis_connection)
        return notifier


class RedisQueue(Queue):
    """
    Durable queue: messages are pickled and kept in a Redis list, so several processes can share it.

    When pickled, e.g. by :class:`~eric_redis_queues.repository.RedisQueueRepository`, only its identity (connection
    data and queue id) is saved: its messages stay in Redis.
    Queues with equal connection data share one client.

    :meth:`pop` without timeout returns immediately, as eric-sse requires. With a timeout it waits for a message:
    this replaces ``BlockingRedisQueue`` of previous versions, callers choose whether to wait, e.g. with
    :meth:`~eric_sse.entities.AbstractChannel.wait_next` or ``queue.pop(timeout=...)``.

    Waits don't poll and don't hold a Redis connection: :meth:`push` publishes a notification on a Pub/Sub channel,
    that one connection per process receives to wake the waiters of the queue. :meth:`wait_pop` waits natively,
    without a thread. A waiter checks the queue once more when its timeout expires, so a lost notification can delay
    a message, never lose it.

    :param redis_connection: Defaults to a local Redis, database 0.
    :param queue_id: Identifies the Redis list. Defaults to a new uuid.
    """

    def __init__(self, redis_connection: RedisConnection | None = None, queue_id: str | None = None):
        self.__redis_connection = redis_connection if redis_connection is not None else RedisConnection()
        self.__queue_id = queue_id if queue_id is not None else generate_uuid()
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

    def __lpop(self) -> bytes | None:
        try:
            return self.__client.lpop(self._key)
        except Exception as e:
            raise RepositoryError(e) from None

    def __push_and_notify(self, raw_message: bytes, front: bool = False) -> None:
        # In a transaction: a pushed message is always notified
        with self.__client.pipeline(transaction=True) as pipe:
            if front:
                pipe.lpush(self._key, raw_message)
            else:
                pipe.rpush(self._key, raw_message)
            pipe.publish(_wake_channel(self.__redis_connection), self.__queue_id)
            pipe.execute()

    def pop(self, timeout: float = 0) -> Any:
        if timeout <= 0:
            raw_value = self.__lpop()
            if raw_value is None:
                raise NoMessagesException
            return loads(raw_value)

        deadline = time.monotonic() + timeout
        woken = threading.Event()
        notifier = _notifier(self.__redis_connection)
        notifier.register(self.__queue_id, woken.set)
        try:
            while True:
                woken.clear()  # Before checking: a push notified after the check wakes the wait below
                raw_value = self.__lpop()
                if raw_value is not None:
                    return loads(raw_value)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise NoMessagesException
                woken.wait(remaining)
        finally:
            notifier.unregister(self.__queue_id, woken.set)

    async def wait_pop(self, timeout: float) -> Any:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        woken = asyncio.Event()

        def wake() -> None:
            try:
                loop.call_soon_threadsafe(woken.set)
            except RuntimeError:
                pass  # Loop already closed

        notifier = _notifier(self.__redis_connection)
        notifier.register(self.__queue_id, wake)
        try:
            while True:
                woken.clear()
                raw_value = await self.__lpop_async()
                if raw_value is not None:
                    return loads(raw_value)
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise NoMessagesException
                try:
                    await asyncio.wait_for(woken.wait(), remaining)
                except asyncio.TimeoutError:
                    pass  # Checks the queue once more before giving up
        finally:
            notifier.unregister(self.__queue_id, wake)

    async def __lpop_async(self) -> bytes | None:
        # The pop runs in a worker thread only for its round trip, so the event loop is never blocked
        popping = asyncio.ensure_future(asyncio.to_thread(self.__lpop))
        try:
            return await asyncio.shield(popping)
        except asyncio.CancelledError:
            # The pop can't be interrupted: a message it gets after the cancellation is put back at the head
            popping.add_done_callback(self.__requeue_popped)
            raise

    def __requeue_popped(self, popping: asyncio.Future) -> None:
        if popping.cancelled() or popping.exception() is not None or popping.result() is None:
            return
        try:
            self.__push_and_notify(popping.result(), front=True)
        except Exception as e:
            logger.error(f'Message popped by a cancelled wait could not be put back in queue {self.__queue_id}: {e!r}')

    def push(self, message: MessageContract) -> None:
        try:
            self.__push_and_notify(dumps(message))
        except Exception as e:
            raise RepositoryError(e) from None

    def purge(self) -> None:
        """Deletes all its messages."""
        try:
            self.__client.delete(self._key)
        except Exception as e:
            raise RepositoryError(e) from None
