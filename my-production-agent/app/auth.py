from fastapi import Header, HTTPException, status
from .config import settings

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Dependency to verify the API key from request headers.
    Returns a generic 'user_id' for simplicity.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include header: X-API-Key: <your-key>"
        )
    
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key."
        )
    
    # In a real app, you might derive user_id from the key or a DB
    return "demo_user"
