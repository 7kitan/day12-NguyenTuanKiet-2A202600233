import redis
from fastapi import HTTPException, status
from .config import settings

# Initialize Redis connection
try:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception:
    r = None

# Mock cost per request
COST_PER_REQUEST = 0.01

async def check_budget(user_id: str):
    """
    Checks if the user has exceeded their monthly budget.
    """
    if r is None:
        return

    key = f"cost:{user_id}"
    budget = settings.MONTHLY_BUDGET_USD
    
    # Get current spending
    current_spending = float(r.get(key) or 0.0)
    
    if current_spending >= budget:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly budget of ${budget} exceeded."
        )

def increment_cost(user_id: str, cost: float = COST_PER_REQUEST):
    """
    Increments the user's spending.
    """
    if r is None:
        return
    
    key = f"cost:{user_id}"
    r.incrbyfloat(key, cost)
