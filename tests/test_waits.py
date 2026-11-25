"""Waits on RedisQueue: native async BLPOP."""
import asyncio
import os
import time
from unittest import IsolatedAsyncioTestCase

from eric_sse.exception import NoMessagesException
from eric_sse.message import Message

from eric_redis_queues import RedisQueue
from tests.redis_fixture import REDIS_CONNECTION, RedisFixture


class WaitsTestCase(RedisFixture, IsolatedAsyncioTestCase):

    async def test_idle_waits_do_not_delay_other_waits(self):
        # More idle waits than the default executor has threads: waits holding a thread would queue up
        idle = [asyncio.create_task(RedisQueue(REDIS_CONNECTION).wait_pop(3)) for _ in range(2 * min(32, os.cpu_count() + 4))]
        queue = RedisQueue(REDIS_CONNECTION)
        active = asyncio.create_task(queue.wait_pop(10))
        await asyncio.sleep(0.2)

        start = time.monotonic()
        queue.push(Message(msg_type='active'))

        self.assertEqual('active', (await active).type)
        self.assertLess(time.monotonic() - start, 1)
        for wait in idle:
            wait.cancel()
        await asyncio.gather(*idle, return_exceptions=True)

    async def test_waits_on_the_same_queue_share_its_messages(self):
        queue = RedisQueue(REDIS_CONNECTION)
        other = RedisQueue(REDIS_CONNECTION, queue_id=queue.queue_id)
        waits = [asyncio.create_task(queue.wait_pop(2)), asyncio.create_task(other.wait_pop(2))]
        await asyncio.sleep(0.05)

        queue.push(Message(msg_type='first'))
        queue.push(Message(msg_type='second'))

        self.assertCountEqual(['first', 'second'], [message.type for message in await asyncio.gather(*waits)])

    async def test_cancelled_wait_leaves_the_message_for_the_next_one(self):
        queue = RedisQueue(REDIS_CONNECTION)
        for _ in range(20):
            waiting = asyncio.create_task(queue.wait_pop(0.5))
            await asyncio.sleep(0.01)
            queue.push(Message(msg_type='kept'))  # Redis serves the waiting BLPOP right away
            waiting.cancel()
            try:
                delivered = await waiting
            except asyncio.CancelledError:
                delivered = None
            if delivered is None:
                self.assertEqual('kept', (await queue.wait_pop(1)).type)
            with self.assertRaises(NoMessagesException):
                queue.pop()
