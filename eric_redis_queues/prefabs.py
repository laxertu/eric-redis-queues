import json
from abc import ABC, abstractmethod
from typing import Iterable

from eric_sse.entities import AbstractChannel
from redis import Redis
from eric_sse.interfaces import ChannelRepositoryInterface
from eric_sse.queues import Queue
from eric_sse.exception import RepositoryError
from eric_sse.prefabs import SSEChannel

from eric_redis_queues import RedisConnection, PREFIX, PREFIX_CHANNELS, PREFIX_QUEUES, PREFIX_LISTENERS


class RedisSSEChannelRepository(ChannelRepositoryInterface, ABC):

    def __init__(self, redis_connection: RedisConnection):
        self.__client: Redis = redis_connection.to_redis_client()

    @abstractmethod
    def create_queue(self) -> Queue:
        ...
    """
    def load_all(self) -> Iterable[AbstractChannel]:
        for redis_key in self._client.scan_iter(f"{ChannelRepository._PREFIX_LISTENERS}:*"):
            key = redis_key.decode()
            try:
                listener = loads(self._client.get(key))
                queue = self.create_queue(listener_id=listener.id)
                yield Connection(listener=listener, queue=queue)
            except Exception as e:
                raise RepositoryError(e)
    """

    def load_all(self) -> Iterable[AbstractChannel]:
        """Returns all channels from the repository."""
        try:
            for redis_key in self.__client.scan_iter(f"{PREFIX_CHANNELS}:*"):
                key = redis_key.decode()
                yield self._fetch_channel_by_key(key)

        except Exception as e:
            raise RepositoryError(e)

    def _fetch_channel_by_key(self, key: str) -> SSEChannel:
        try:
            channel_construction_params: dict[str] = json.loads(self.__client.get(key))
            channel = SSEChannel(**channel_construction_params)
            return channel

        except Exception as e:
            raise RepositoryError(e)

    def load_one(self, channel_id: str) -> AbstractChannel:
        return self._fetch_channel_by_key(RedisSSEChannelRepository._build_redis_key(channel_id))

    @staticmethod
    def _build_redis_key(channel_id: str) -> str:
        return f'{PREFIX_CHANNELS}:{channel_id}'

    @staticmethod
    def _get_constructor_params(channel: SSEChannel) -> dict[str, any]:
        return {
            'stream_delay_seconds': channel.stream_delay_seconds,
            'retry_timeout_milliseconds': channel.retry_timeout_milliseconds,
            'channel_id': channel.id
        }

    def persist(self, channel: SSEChannel):
        try:
            self.__client.set(
                channel.id,
                json.dumps(RedisSSEChannelRepository._get_constructor_params(channel))
            )
        except Exception as e:
            raise RepositoryError(e)

    def delete(self, channel_id: str):
        try:
            self.__client.delete(channel_id)
        except Exception as e:
            raise RepositoryError(e)
