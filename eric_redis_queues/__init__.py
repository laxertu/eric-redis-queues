import json
from abc import ABC
from typing import Iterable, Any
from pickle import dumps, loads

from redis import Redis
from eric_sse import get_logger
from eric_sse.exception import NoMessagesException, RepositoryError
from eric_sse.message import MessageContract
from eric_sse.prefabs import SSEChannel
from eric_sse.interfaces import ConnectionRepositoryInterface, ChannelRepositoryInterface
from eric_sse.persistence import ItemNotFound
from eric_sse.serializable import ConnectionRepository, QueueRepository, ChannelRepository

from eric_redis_queues.core import RedisStorage, AbstractRedisQueue

logger = get_logger()

_PREFIX = 'eric-redis-queues'
_PREFIX_QUEUES = f'eric-redis-queues:q'
_PREFIX_LISTENERS = f'eric-redis-queues:l'
_PREFIX_CHANNELS = f'eric-redis-queues:c'

CONNECTION_REPOSITORY_DEFAULT = 'eric_redis_queues.RedisConnectionsRepository'
CONNECTION_REPOSITORY_BLOCKING = 'eric_redis_queues.RedisBlockingQueuesRepository'


class RedisQueue(AbstractRedisQueue):


    def pop(self) -> Any | None:
        try:
            raw_value = self._client.lpop(f'{_PREFIX_QUEUES}:{self.kv_key}')
            if raw_value is None:
                raise NoMessagesException
            return loads(bytes(raw_value))

        except NoMessagesException:
            raise
        except Exception as e:
            raise RepositoryError(e)


    def push(self, msg: MessageContract) -> None:
        try:
            self._client.rpush(f'{_PREFIX_QUEUES}:{self.kv_key}', dumps(msg))
        except Exception as e:
            raise RepositoryError(e)

class BlockingRedisQueue(RedisQueue):
    """Implements a blocking queue. See **pop()** documentation"""

    def pop(self) -> Any | None:
        """Behaviour relies on https://redis.io/docs/latest/commands/blpop/ , so calls to it with block program execution until a new message is pushed."""

        k, v = self._client.blpop([f'{_PREFIX_QUEUES}:{self.kv_key}'])
        return loads(bytes(v))

class AbstractRedisConnectionRepository(ConnectionRepository, ABC):
    def __init__(self, host='127.0.0.1', port=6379, db=0,
                 connection_factory: str = CONNECTION_REPOSITORY_DEFAULT):

        super().__init__(RedisStorage(_PREFIX_LISTENERS, host, port, db))
        self._host: str = host
        self._port: int = port
        self._db: int = db
        self.__listeners_repository = RedisSSEListenersRepository(
            RedisStorage(_PREFIX_LISTENERS, host=host, port=port, db=db)
        )

        self.__queues_repositories_constructors = {
            CONNECTION_REPOSITORY_DEFAULT: RedisNonBlockingQueuesRepository,
            CONNECTION_REPOSITORY_BLOCKING: RedisBlockingQueuesRepository,
        }

        self.__queues_repository = self.__create_queues_repository(connection_factory)

    def __create_queues_repository(self, class_name: str) -> ConnectionRepositoryInterface:
        try:
            constructor = self.__queues_repositories_constructors[class_name]
        except KeyError as e:
            raise RepositoryError(f"Unknown repository class {class_name}") from e
        return constructor(host=self._host, port=self._port, db=self._db)



class RedisSSEListenersRepository(QueueRepository):

    def __init__(self, storage: RedisStorage):
        super().__init__(storage_engine=storage)

class RedisNonBlockingQueuesRepository(QueueRepository):


    def create_queue(self, listener_id: str, host: str, port: int, db: int) -> RedisQueue:
        return RedisQueue(listener_id=listener_id, host=host, port=port, db=db)

class RedisBlockingQueuesRepository(AbstractRedisConnectionRepository):


    def create_queue(self, listener_id: str) -> BlockingRedisQueue:
        """Creates a new blocking queue."""
        return BlockingRedisQueue(listener_id= listener_id, host=self._host, port=self._port, db=self._db)


class RedisSSEChannelRepository(ChannelRepositoryInterface):


    def __init__(self, connection_repository: ConnectionRepositoryInterface, host='127.0.0.1', port=6379, db=0):
        """
        :param host:
        :param port:
        :param db:
        :param connection_repository: Connection factory name to use to connect to Redis. Accepted literals are **'RedisConnectionsRepository'** and **'RedisBlockingQueuesRepository'**
        """
        self.__host: str = host
        self.__port: int = port
        self.__db: int = db
        self.__client = Redis(host=host, port=port, db=db)
        self.__connection_repository = connection_repository


    def _fetch_channel_by_key(self, key: str) -> SSEChannel:
        try:
            channel_construction_params: dict[str] = json.loads(self.__client.get(key).decode())
            if channel_construction_params is None:
                raise ItemNotFound(f"Channel {key} doesn't exist")

            channel = SSEChannel(**channel_construction_params)
            for connection in self.__connection_repository.load_all(channel_id=channel.id):
                channel.register_connection(listener=connection.listener, queue=connection.queue)
            return channel

        except Exception as e:
            raise RepositoryError from e

    def load_one(self, channel_id: str) -> SSEChannel:
        key = f'{_PREFIX_CHANNELS}:{channel_id}'
        return self._fetch_channel_by_key(key)

    def load_all(self) -> Iterable[SSEChannel]:
        """Returns all channels from the repository."""
        try:
            for redis_key in self.__client.scan_iter(f"{_PREFIX_CHANNELS}:*"):
                key = redis_key.decode()
                yield self._fetch_channel_by_key(key)

        except Exception as e:
            raise RepositoryError(e)

    def persist(self, persistable: SSEChannel):
        try:
            data_to_persist = persistable.kv_setup_values_as_dict
            self.__client.set(f'{_PREFIX_CHANNELS}:{persistable.id}', json.dumps(data_to_persist))
        except Exception as e:
            raise RepositoryError(e)

    def delete(self, key: str):
        try:
            for connection in self.__connection_repository.load_all(key):
                self.__connection_repository.delete(connection_id=connection.id)
        except Exception as e:
            raise RepositoryError(e)
