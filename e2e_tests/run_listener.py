from eric_redis_queues import RedisEventListener

key = input("key: ")

l = RedisEventListener()

for x in l.listen(key):
    print(x.type)
    print(x.payload)
