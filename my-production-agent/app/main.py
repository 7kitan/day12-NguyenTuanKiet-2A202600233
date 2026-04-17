import json
import logging
import os
import signal
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import redis
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget, increment_cost
from utils.mock_llm import ask

# ── Structured Logging Configuration ──
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
        }
        return json.dumps(log_entry)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("app")
logger.addHandler(handler)
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger.propagate = False

# ── Global Variables & Redis ──
INSTANCE_ID = f"instance-{uuid.uuid4().hex[:6]}"
START_TIME = time.time()
_in_flight_requests = 0
_is_ready = False

try:
    _redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    _redis = redis.Redis(connection_pool=_redis_pool)
    logger.info("Initializing Redis connectivity check...")
except Exception as e:
    _redis = None
    logger.error(f"Failed to initialize Redis pool: {e}")

# ── Lifecycle Management ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(f"🚀 Starting Production Agent: {INSTANCE_ID}")
    
    # Verify Redis
    try:
        if _redis:
            _redis.ping()
            _is_ready = True
            logger.info("✅ Redis connected and ready")
        else:
            raise RuntimeError("Redis client not initialized")
    except Exception as e:
        logger.error(f"❌ Readiness Check Failed: {e}")
        _is_ready = False
    
    yield
    
    # ── Graceful Shutdown ──
    _is_ready = False
    logger.info("🔄 Shutting down gracefully...")
    
    timeout = 30
    wait_start = time.time()
    while _in_flight_requests > 0 and (time.time() - wait_start) < timeout:
        logger.info(f"Waiting for {_in_flight_requests} active requests to finish...")
        time.sleep(1)
    
    logger.info("👋 Shutdown complete")

# ── FastAPI App Setup ──
app = FastAPI(
    title="Production AI Agent",
    description="Scalable, Secure, and Reliable AI Agent",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def monitor_requests(request, call_next):
    global _in_flight_requests
    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1

# ── Data Models ──
class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

# ── Endpoints ──

@app.get("/")
def index():
    """Welcome endpoint for visual verification."""
    return {
        "message": "Production AI Agent is live!",
        "version": "1.0.0",
        "instance": INSTANCE_ID,
        "docs": "/docs"
    }


@app.get("/health")
def health():
    """Liveness probe."""
    return {
        "status": "ok",
        "instance": INSTANCE_ID,
        "uptime": round(time.time() - START_TIME, 2)
    }

@app.get("/ready")
def ready():
    """Readiness probe."""
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    try:
        _redis.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Redis connection lost")
    return {"status": "ready", "instance": INSTANCE_ID}

@app.post("/ask")
async def chat(
    body: ChatRequest,
    user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget)
):
    """
    Stateful chat endpoint using Redis Lists for history.
    Enforces Authentication, Rate Limiting, and Budget Protection.
    """
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Service shutting down")

    session_id = body.session_id or str(uuid.uuid4())
    history_key = f"history:{session_id}"

    # 1. Add user message to history
    user_msg = json.dumps({"role": "user", "content": body.question, "time": time.time()})
    _redis.rpush(history_key, user_msg)
    _redis.ltrim(history_key, -20, -1)
    _redis.expire(history_key, 3600)

    # 2. Call Mock LLM
    answer = ask(body.question)

    # 3. Add assistant response to history
    assistant_msg = json.dumps({"role": "assistant", "content": answer, "time": time.time()})
    _redis.rpush(history_key, assistant_msg)
    _redis.ltrim(history_key, -20, -1)

    # 4. Charge user
    increment_cost(user_id)

    # 5. Return result
    raw_history = _redis.lrange(history_key, 0, -1)
    history = [json.loads(m) for m in raw_history]

    return {
        "session_id": session_id,
        "answer": answer,
        "turn": len([m for m in history if m["role"] == "user"]),
        "served_by": INSTANCE_ID
    }

# Logic to handle signals for Uvicorn
def handle_exit(sig, frame):
    logger.info(f"Signal {sig} received")

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)
