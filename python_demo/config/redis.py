import redis.asyncio as redis

redis_client = redis.Redis(
    host='39.107.193.66',
    port=6379,
    password='rootroot',
    db=0,
    decode_responses=True
)

async def set_key(key: str, value: str, ex: int = None):
    """
    设置键值对，ex为过期时间（秒），可选。
    """
    return await redis_client.set(key, value, ex=ex)

async def get_key(key: str):
    """
    获取指定key的值。
    """
    return await redis_client.get(key)