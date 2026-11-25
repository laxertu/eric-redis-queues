"""Redis implementations checked against eric-sse contracts."""
import logging
from unittest import IsolatedAsyncioTestCase, TestCase

from eric_sse.builder import ChannelRepositoryBuilder
from eric_sse.contracts.channel import ChannelContract
from eric_sse.contracts.error_handling import ChannelErrorHandlingContract
from eric_sse.contracts.queue import QueueContract
from eric_sse.contracts.repository import ChannelRepositoryContract
from eric_sse.prefabs import SSEChannel
from eric_sse.repository import PrefixedStorage

from eric_redis_queues import RedisStorage
from eric_redis_queues.repository import RedisQueueRepository, redis_channel_repository_builder
from tests.redis_fixture import REDIS_CONNECTION, RedisFixture


def redis_builder() -> ChannelRepositoryBuilder:
    return redis_channel_repository_builder(SSEChannel, REDIS_CONNECTION)


class RedisChannelRepositoryTestCase(RedisFixture, ChannelRepositoryContract, TestCase):
    def create_builder(self) -> ChannelRepositoryBuilder:
        return redis_builder()

    def channel_data(self) -> dict:
        return {'retry_timeout_milliseconds': 10, 'stream_delay_seconds': 1}


class RedisQueueTestCase(RedisFixture, QueueContract, IsolatedAsyncioTestCase):
    def create_builder(self) -> ChannelRepositoryBuilder:
        return redis_builder()

    def channel_data(self) -> dict:
        return {}


class RedisChannelTestCase(RedisFixture, ChannelContract, IsolatedAsyncioTestCase):
    def create_builder(self) -> ChannelRepositoryBuilder:
        return redis_builder()

    def channel_data(self) -> dict:
        return {}


class RedisChannelErrorHandlingTestCase(RedisFixture, ChannelErrorHandlingContract, IsolatedAsyncioTestCase):
    """
    Channels, connections, listeners and queues are in Redis, except the contract's failing doubles: its
    ``BrokenQueue`` is an ``InMemoryQueue``, that can't be pickled, so the builder's default storage, used for
    the parts the contract replaces, stays in memory. See https://github.com/laxertu/eric/issues/53
    """

    def setUp(self):
        super().setUp()
        # The contract checks tracebacks logged at DEBUG level, while eric_sse.get_logger() sets INFO
        eric_logger = logging.getLogger('eric_sse')
        self.addCleanup(eric_logger.setLevel, eric_logger.level)
        eric_logger.setLevel(logging.DEBUG)

    def create_builder(self) -> ChannelRepositoryBuilder:
        storage = RedisStorage(REDIS_CONNECTION)
        return (
            ChannelRepositoryBuilder(SSEChannel)
            .channels(PrefixedStorage(storage, 'channel:'))
            .connections(PrefixedStorage(storage, 'connection:'))
            .listeners(storage=PrefixedStorage(storage, 'listener:'))
            .queues_repository(RedisQueueRepository(REDIS_CONNECTION, PrefixedStorage(storage, 'queue:')))
        )

    def channel_data(self) -> dict:
        return {}
