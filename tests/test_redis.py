"""Redis specific behaviours, not covered by eric-sse contracts."""
import pickle
from unittest import TestCase

from eric_sse.exception import ItemNotFound, NoMessagesException
from eric_sse.message import Message
from eric_sse.prefabs import SSEChannel

from eric_redis_queues import RedisQueue, RedisStorage
from eric_redis_queues.repository import RedisQueueRepository, redis_channel_repository_builder
from tests.redis_fixture import REDIS_CLIENT, REDIS_CONNECTION, RedisFixture


class RedisQueueTestCase(RedisFixture, TestCase):

    def test_queues_with_the_same_id_share_messages(self):
        producer = RedisQueue(REDIS_CONNECTION)
        consumer = RedisQueue(REDIS_CONNECTION, queue_id=producer.queue_id)

        producer.push(Message(msg_type='test'))

        self.assertEqual('test', consumer.pop().type)

    def test_unpickled_queue_keeps_its_identity_and_messages(self):
        queue = RedisQueue(REDIS_CONNECTION)
        queue.push(Message(msg_type='test'))

        unpickled = pickle.loads(pickle.dumps(queue))

        self.assertEqual((queue.queue_id, queue.redis_connection), (unpickled.queue_id, unpickled.redis_connection))
        self.assertEqual('test', unpickled.pop().type)

    def test_queues_with_the_same_connection_share_a_client(self):
        first, second = RedisQueue(REDIS_CONNECTION), RedisQueue(REDIS_CONNECTION)

        self.assertIs(first._RedisQueue__client, second._RedisQueue__client)

    def test_purge_deletes_messages(self):
        queue = RedisQueue(REDIS_CONNECTION)
        queue.push(Message(msg_type='test'))

        queue.purge()

        with self.assertRaises(NoMessagesException):
            queue.pop()


class RedisStorageTestCase(RedisFixture, TestCase):

    def test_prefix_glob_characters_are_matched_literally(self):
        storage = RedisStorage(REDIS_CONNECTION)
        storage.upsert('a*:1', 'star')
        storage.upsert('ab:1', 'other')
        storage.upsert('a?[]\\:1', 'specials')

        self.assertEqual(['star'], list(storage.fetch_by_prefix('a*')))
        self.assertEqual(['specials'], list(storage.fetch_by_prefix('a?[]\\')))

    def test_missing_key_is_not_found_and_deletion_is_idempotent(self):
        storage = RedisStorage(REDIS_CONNECTION)

        with self.assertRaises(ItemNotFound):
            storage.fetch_one('missing')
        storage.delete('missing')

    def test_storages_with_different_prefixes_do_not_mix(self):
        first = RedisStorage(REDIS_CONNECTION, prefix='eric-redis-queues:test-1:')
        second = RedisStorage(REDIS_CONNECTION, prefix='eric-redis-queues:test-2:')
        first.upsert('key', 'first')

        self.assertEqual(['first'], list(first.fetch_by_prefix('')))
        self.assertEqual([], list(second.fetch_by_prefix('')))


class RedisQueueRepositoryTestCase(RedisFixture, TestCase):

    def test_loaded_queues_keep_their_identity_and_messages(self):
        repository = RedisQueueRepository(REDIS_CONNECTION, RedisStorage(REDIS_CONNECTION))
        queue = repository.create()
        queue.push(Message(msg_type='test'))

        repository.persist('connection', queue)

        loaded = repository.load('connection')
        self.assertEqual((queue.queue_id, REDIS_CONNECTION), (loaded.queue_id, loaded.redis_connection))
        self.assertEqual('test', loaded.pop().type)


class RedisRepositoryTestCase(RedisFixture, TestCase):

    def test_messages_dispatched_after_persist_are_seen_by_another_repository(self):
        # As if producer and consumer were different processes: no persist is needed after dispatching
        producer = redis_channel_repository_builder(SSEChannel, REDIS_CONNECTION).build()
        consumer = redis_channel_repository_builder(SSEChannel, REDIS_CONNECTION).build()
        channel = producer.create({})
        connection = channel.add_connection()
        producer.persist(channel)

        channel.dispatch(connection.id, Message(msg_type='test', msg_payload='hello'))

        loaded = consumer.load_one(channel.id)
        loaded.get_connection(connection.id).listener.start()
        self.assertEqual('hello', loaded.deliver_next(connection.id).payload)

    def test_deleting_a_channel_deletes_its_queued_messages(self):
        repository = redis_channel_repository_builder(SSEChannel, REDIS_CONNECTION).build()
        channel = repository.create({})
        connection = channel.add_connection()
        channel.dispatch(connection.id, Message(msg_type='test'))
        repository.persist(channel)

        repository.delete(channel.id)

        client = REDIS_CLIENT
        self.assertEqual([], list(client.scan_iter(match='eric-redis-queues:*')))
