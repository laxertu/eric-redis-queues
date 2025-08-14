from abc import ABC
from pickle import loads
from typing import Iterable

from eric_sse.persistence import KvStorageEngine
from eric_sse.queues import PersistableQueue
from redis import Redis


class RedisStorage(KvStorageEngine):

    def __init__(self, kv_prefix: str, host='127.0.0.1', port=6379, db=0):
        self.__kv_prefix = kv_prefix
        self._client = Redis(host=host, port=port, db=db)

    def __fetch_by_prefix(self, prefix: str) -> Iterable[any]:
        for redis_key in self._client.scan_iter(prefix):
            yield loads(self._client.get(redis_key))

    def fetch_all(self) -> Iterable[any]:
        return self.__fetch_by_prefix(f"{self.__kv_prefix}:*")

    def fetch_by_prefix(self, prefix: str) -> Iterable[any]:
        return self.__fetch_by_prefix(f"{self.__kv_prefix}:{prefix}")

    def upsert(self, key: str, value: any):
        self._client.set(key, value)

    def fetch_one(self, key: str) -> any:
        return self._client.get(key)

    def delete(self, key: str):
        self._client.delete(key)


class AbstractRedisQueue(PersistableQueue, ABC):

    def __init__(self, listener_id: str, host='127.0.0.1', port=6379, db=0):

        super().__init__()
        self.__id: str | None = None
        self._client: Redis | None = None

        self.__host: str | None = None
        self.__port: int | None = None
        self.__db: int | None = None
        self.__value_as_dict = {}

        self.kv_setup_by_dict({
            'listener_id': listener_id,
            'host': host,
            'port': port,
            'db': db
        })

    @property
    def kv_key(self) -> str:
        return self.__id

    @property
    def kv_setup_values_as_dict(self):
        return self.__value_as_dict

    def kv_setup_by_dict(self, setup: dict):
        self.__id = setup['listener_id']
        self.__host = setup['host']
        self.__port = setup['port']
        self.__db = setup['db']
        self.__value_as_dict.update(setup)
        self._client = Redis(host=self.__host, port=self.__port, db=self.__db)

    @property
    def kv_constructor_params_as_dict(self) -> dict:
        return {
            'listener_id': self.__id,
            'host': self.__host,
            'port': self.__port,
            'db': self.__db,
        }
