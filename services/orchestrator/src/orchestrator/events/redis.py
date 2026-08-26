from redis.asyncio import Redis

redis_client = Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)
