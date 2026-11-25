"""Waits on RedisQueue: woken by Pub/Sub notifications, without polling or holding a Redis connection."""
import asyncio
import os
import pickle
import threading
import time
from unittest import IsolatedAsyncioTestCase

from eric_sse.exception import NoMessagesException
from eric_sse.message import Message

from eric_redis_queues import NOTIFIER_CLIENT_NAME, RedisQueue, _wake_channel
from tests.redis_fixture import REDIS_CLIENT, REDIS_CONNECTION, RedisFixture


def push_from_another_process(queue: RedisQueue, message: Message) -> None:
    """What another process's push sends: the message, then its notification."""
    REDIS_CLIENT.rpush(queue._key, pickle.dumps(message))
    REDIS_CLIENT.publish(_wake_channel(REDIS_CONNECTION), queue.queue_id)


def push_without_notification(queue: RedisQueue, message: Message) -> None:
    """As if the notification was lost."""
    REDIS_CLIENT.rpush(queue._key, pickle.dumps(message))


class WakeUpsTestCase(RedisFixture, IsolatedAsyncioTestCase):

    async def test_idle_waits_neither_block_redis_connections_nor_delay_other_waits(self):
        # More idle waits than the default executor has threads: waits running a blocking pop in a thread would hold
        # a Redis connection each, and queue up the next waits until they time out
        executor_threads = min(32, (os.cpu_count() or 1) + 4)
        idle = [asyncio.create_task(RedisQueue(REDIS_CONNECTION).wait_pop(3)) for _ in range(2 * executor_threads)]
        queue = RedisQueue(REDIS_CONNECTION)
        active = asyncio.create_task(queue.wait_pop(10))
        await asyncio.sleep(0.2)

        blocked_clients = [
            client for client in REDIS_CLIENT.client_list()
            if 'b' in client['flags'] and int(client['db']) == REDIS_CONNECTION.db
        ]
        start = time.monotonic()
        queue.push(Message(msg_type='active'))
        received = await active
        elapsed = time.monotonic() - start
        for wait in idle:
            wait.cancel()
        await asyncio.gather(*idle, return_exceptions=True)

        self.assertEqual([], blocked_clients)
        self.assertEqual('active', received.type)
        self.assertLess(elapsed, 1)

    async def test_push_from_another_process_wakes_the_wait(self):
        queue = RedisQueue(REDIS_CONNECTION)
        asyncio.get_running_loop().call_later(0.05, push_from_another_process, queue, Message(msg_type='late'))
        start = time.monotonic()

        self.assertEqual('late', (await queue.wait_pop(5)).type)
        self.assertLess(time.monotonic() - start, 1)

    async def test_message_without_notification_is_found_when_the_wait_times_out(self):
        queue = RedisQueue(REDIS_CONNECTION)
        asyncio.get_running_loop().call_later(0.05, push_without_notification, queue, Message(msg_type='async'))

        self.assertEqual('async', (await queue.wait_pop(0.3)).type)

        threading.Timer(0.05, push_without_notification, args=(queue, Message(msg_type='sync'))).start()
        self.assertEqual('sync', (await asyncio.to_thread(queue.pop, 0.3)).type)

    async def test_waits_recover_when_the_notifications_connection_is_lost(self):
        queue = RedisQueue(REDIS_CONNECTION)
        with self.assertRaises(NoMessagesException):
            await queue.wait_pop(0.1)  # The notifier is subscribed
        waiting = asyncio.create_task(queue.wait_pop(10))
        await asyncio.sleep(0.05)

        killed = [
            REDIS_CLIENT.client_kill_filter(_id=client['id'])
            for client in REDIS_CLIENT.client_list() if client['name'] == NOTIFIER_CLIENT_NAME
        ]
        self.assertTrue(killed)
        await asyncio.sleep(0.05)
        start = time.monotonic()
        queue.push(Message(msg_type='after reconnection'))

        self.assertEqual('after reconnection', (await waiting).type)
        self.assertLess(time.monotonic() - start, 5)

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
        for _ in range(20):  # Cancels at different points of the wait, including during a pop
            waiting = asyncio.create_task(queue.wait_pop(2))
            await asyncio.sleep(0)
            queue.push(Message(msg_type='kept'))
            await asyncio.sleep(0)
            waiting.cancel()
            try:
                delivered = await waiting
            except asyncio.CancelledError:
                delivered = None
            if delivered is None:
                await asyncio.sleep(0.05)  # Lets a message popped by the cancelled wait be put back
                self.assertEqual('kept', (await queue.wait_pop(1)).type)
            with self.assertRaises(NoMessagesException):
                queue.pop()
