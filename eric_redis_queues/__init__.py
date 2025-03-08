from uuid import uuid4
from pickle import dumps, loads

from redis import Redis

from eric_sse.entities import AbstractChannel, MessageQueueListener
from eric_sse.exception import NoMessagesException
from eric_sse.message import MessageContract
from eric_sse.queue import Queue, AbstractMessageQueueFactory, RepositoryError

_PREFIX = 'eric_queues'

class RedisQueue(Queue):

    def __init__(self, host='127.0.0.1', port=6379, db=0):
        self.id = str(uuid4())
        self.__client = Redis(host=host, port=port, db=db)

    def bind(self, queue_id: str):
        self.id = queue_id

    def pop(self) -> MessageContract:

        if not self.__client.exists(self.id):
            raise NoMessagesException

        try:
            raw_value = self.__client.lpop(self.id)
            return loads(raw_value)

        except Exception as e:
            raise RepositoryError(e)


    def push(self, msg: MessageContract) -> None:
        try:
            self.__client.rpush(f'{_PREFIX}:{self.id}', dumps(msg))
        except Exception as e:
            raise RepositoryError(e)

    def delete(self) -> None:
        self.__client.delete(self.id)


class RedisQueueFactory(AbstractMessageQueueFactory):
    def __init__(self, host='127.0.0.1', port=6379, db=0):
        self.__host: str = host
        self.__port: int = port
        self.__db: int = db

    def create(self) -> Queue:
        return RedisQueue(host=self.__host, port=self.__port, db=self.__db)

    def load(self, queue_id: str) -> RedisQueue:
        redis_queue = RedisQueue(host=self.__host, port=self.__port, db=self.__db)
        redis_queue.bind(queue_id)

        return redis_queue

class RedisChannel(AbstractChannel):
    def __init__(self, host='127.0.0.1', port=6379, db=0):
        try:
            super().__init__()
            f = RedisQueueFactory(host=host, port=port, db=db)
            self._set_queues_factory(f)

            redis_client = Redis(host=host, port=port, db=db)
            for redis_queue in redis_client.scan_iter(f"{_PREFIX}:*"):
                print(redis_queue.decode())
                queue = f.load(redis_queue.decode())
                listener = MessageQueueListener()
                listener.id = redis_queue.decode()
                self.register_listener(listener)
                self._set_queue(listener_id=listener.id, queue=queue)

        except Exception as e:
            raise RepositoryError(e)

    def adapt(self, msg: MessageContract) -> MessageContract:
        return msg