import time
import redis
from fastapi import HTTPException, status
from .config import settings

# Initialize Redis connection
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    # We will handle connection failure in the readiness probe/lifespan
    r = None

async def check_rate_limit(user_id: str):
    """
    Sliding window rate limiter using Redis sorted sets.
    Limit: 10 requests per minute.
    """
    if r is None:
        # Fallback if Redis is down (though production should fail)
        return

    now = time.time()
    key = f"rate_limit:{user_id}"
    window = 60  # 1 minute
    limit = settings.RATE_LIMIT_PER_MINUTE

    # Use a Lua script or multi-exec for atomicity
    pipe = r.pipeline()
    # Remove entries older than the window
    pipe.zremrangebyscore(key, 0, now - window)
    # Count entries in the current window
    pipe.zcard(key)
    # Add the current request
    pipe.zadd(key, {str(now): now})
    # Set expiration on the key to clean up
    pipe.expire(key, window)
    
    results = pipe.execute()
    count = results[1]

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {limit} requests per minute."
        )
