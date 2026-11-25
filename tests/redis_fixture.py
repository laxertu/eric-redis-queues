"""
Integration tests need a running Redis. Configure it with the environment variables ``REDIS_HOST`` (default
127.0.0.1), ``REDIS_PORT`` (default 6379) and ``REDIS_DB`` (default 15).

Only keys of this library (``eric-redis-queues:*``) are deleted, before each test. Tests are skipped if Redis is
not reachable.
"""
import os
from unittest import SkipTest

from redis.exceptions import ConnectionError as RedisConnectionError

from eric_redis_queues import PREFIX, RedisConnection

REDIS_CONNECTION = RedisConnection(
    host=os.environ.get('REDIS_HOST', '127.0.0.1'),
    port=int(os.environ.get('REDIS_PORT', '6379')),
    db=int(os.environ.get('REDIS_DB', '15')),
)
REDIS_CLIENT = REDIS_CONNECTION.create_client()


def clean_redis() -> None:
    try:
        keys = list(REDIS_CLIENT.scan_iter(match=f'{PREFIX}:*', count=1000))
    except RedisConnectionError as e:
        raise SkipTest(f'Redis not reachable: {e}') from None
    if keys:
        REDIS_CLIENT.delete(*keys)


class RedisFixture:
    """Mixin cleaning this library's keys before each test."""

    def setUp(self):
        clean_redis()
        super().setUp()
