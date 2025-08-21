
from redis import Redis

r = Redis()
for k in r.scan_iter('*'):
    r.delete(k)
