import redis

from core import settings

HOST = settings.db.redis_host
PORT = 6379
DB = settings.db.redis_db

redis_client = redis.Redis(host=HOST, port=PORT, db=DB)
REDIS_PATH = f"redis://{HOST}:{PORT}/{DB}"