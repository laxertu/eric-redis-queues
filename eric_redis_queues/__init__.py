from dataclasses import dataclass
from pickle import loads, dumps
from abc import ABC
from typing import Any

from redis import Redis

from eric_sse import generate_uuid
from eric_sse.queues import Queue
from eric_sse.exception import NoMessagesException, RepositoryError
from eric_sse.entities import MessageContract

PREFIX = 'eric-redis-queues'
PREFIX_QUEUES = f'{PREFIX}:q'


@dataclass
class RedisConnection:
    host: str = '127.0.0.1'
    port: int = 6379
    db: int = 0

    def to_redis_client(self) -> Redis:
        return Redis(host=self.host, port=self.port, db=self.db)

class AbstractRedisQueue(Queue, ABC):

    def __init__(self, host='127.0.0.1', port=6379, db=0, queue_id: str | None = None):
        self.__id: str = queue_id if queue_id else generate_uuid()
        self._client: Redis | None = None

        self.__host: str | None = None
        self.__port: int | None = None
        self.__db: int | None = None
        self.__value_as_dict = {
            'queue_id': queue_id,
            'host': host,
            'port': port,
            'db': db
        }

    @property
    def id(self) -> str:
        return self.__id

    def push(self, msg: MessageContract) -> None:
        try:
            self._client.rpush(f'{PREFIX_QUEUES}:{self.id}', dumps(msg))
        except Exception as e:
            raise RepositoryError(e)

class RedisQueue(AbstractRedisQueue):


    def pop(self) -> Any | None:
        try:
            raw_value = self._client.lpop(f'{PREFIX_QUEUES}:{self.id}')
            if raw_value is None:
                raise NoMessagesException
            return loads(bytes(raw_value))

        except NoMessagesException:
            raise
        except Exception as e:
            raise RepositoryError(e)


class BlockingRedisQueue(RedisQueue):
    """Implements a blocking queue. See **pop()** documentation"""

    def pop(self) -> Any | None:
        """Behaviour relies on https://redis.io/docs/latest/commands/blpop/ , so calls to it with block program execution until a new message is pushed."""

        k, v = self._client.blpop([f'{PREFIX_QUEUES}:{self.id}'])
        return loads(bytes(v))


