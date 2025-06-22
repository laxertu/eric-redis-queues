from eric_redis_queues import RedisQueueFactory

def reset_factory(host='127.0.0.1', port=6379, db=0):
    f = RedisQueueFactory(host=host, port=port, db=db)
    f.reset_repository()