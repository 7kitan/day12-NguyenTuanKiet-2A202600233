"""
ADVANCED — Stateless Agent với Redis Session

Stateless = agent không giữ state trong memory.
Mọi state (session, conversation history) lưu trong Redis.

Tại sao stateless quan trọng khi scale?
  Instance 1: User A gửi request 1 → lưu session trong memory
  Instance 2: User A gửi request 2 → KHÔNG có session! Bug!

  ✅ Giải pháp: Lưu session trong Redis
  Bất kỳ instance nào cũng đọc được session của user.

Demo:
  docker compose up
  # Sau đó test multi-turn conversation
  python test_stateless.py
"""

import json
import logging
import os
import time
import uuid
import signal
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.mock_llm import ask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Redis (Stateless Requirement)
try:
    import redis

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Sử dụng ConnectionPool để quản lý kết nối hiệu quả hơn
    pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
    _redis = redis.Redis(connection_pool=pool)
    _redis.ping()
    logger.info("✅ Connected to Redis")
except Exception as e:
    logger.error(f"❌ Critical error: Could not connect to Redis: {e}")
    # Trong môi trường stateless, không có Redis = không thể hoạt động
    raise RuntimeError("Redis is required for stateless design.")

START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")
_in_flight_requests = 0  # Theo dõi số request đang xử lý
_is_ready = False


# ──────────────────────────────────────────────────────────
# Session Storage (Redis-backed, Stateless-compatible)
# ──────────────────────────────────────────────────────────


def append_to_history(session_id: str, role: str, content: str):
    """Thêm message vào conversation history dùng Redis List."""
    key = f"history:{session_id}"
    message = json.dumps({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    # 1. Thêm vào cuối list
    _redis.rpush(key, message)
    
    # 2. Giữ tối đa 20 messages (10 turns)
    _redis.ltrim(key, -20, -1)
    
    # 3. Set TTL cho session (1 hour)
    _redis.expire(key, 3600)


def load_history(session_id: str) -> list:
    """Load conversation history từ Redis List."""
    key = f"history:{session_id}"
    data = _redis.lrange(key, 0, -1)
    return [json.loads(m) for m in data]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(f"🚀 Starting instance {INSTANCE_ID}")
    
    # Model/Dependencies loading simulation
    time.sleep(0.1)
    _is_ready = True
    logger.info(f"✅ Instance {INSTANCE_ID} is ready")
    
    yield
    
    # ── Graceful Shutdown ──
    _is_ready = False
    logger.info(f"🔄 Instance {INSTANCE_ID} shutting down...")
    
    # Chờ cho các request đang xử lý hoàn thành (timeout 30s)
    timeout = 30
    start_wait = time.time()
    while _in_flight_requests > 0 and (time.time() - start_wait) < timeout:
        logger.info(f"Waiting for {_in_flight_requests} active requests...")
        time.sleep(1)
        
    logger.info(f"👋 Instance {INSTANCE_ID} shutdown complete")


app = FastAPI(
    title="Stateless Agent",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_requests(request, call_next):
    """Middleware để theo dõi số lượng request đang xử lý nhằm phục vụ Graceful Shutdown."""
    global _in_flight_requests
    _in_flight_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        _in_flight_requests -= 1


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────


@app.post("/chat")
async def chat(body: ChatRequest):
    """
    Multi-turn conversation với session management.

    Gửi session_id trong các request tiếp theo để tiếp tục cuộc trò chuyện.
    Agent có thể chạy trên bất kỳ instance nào — state trong Redis.
    """
    if not _is_ready:
        raise HTTPException(503, "Instance is shutting down")

    # Tạo hoặc dùng session hiện có
    session_id = body.session_id or str(uuid.uuid4())

    # Thêm câu hỏi vào history (Redis List)
    append_to_history(session_id, "user", body.question)

    # Gọi LLM (mock)
    answer = ask(body.question)

    # Lưu response vào history (Redis List)
    append_to_history(session_id, "assistant", answer)

    # Lấy history mới nhất để tính turn count
    history = load_history(session_id)

    return {
        "session_id": session_id,
        "question": body.question,
        "answer": answer,
        "turn": len([m for m in history if m["role"] == "user"]),
        "served_by": INSTANCE_ID,
        "storage": "redis"
    }


@app.get("/chat/{session_id}/history")
def get_chat_history(session_id: str):
    """Xem conversation history của một session từ Redis."""
    history = load_history(session_id)
    if not history:
        raise HTTPException(404, f"Session {session_id} not found or expired")
    return {
        "session_id": session_id,
        "messages": history,
        "count": len(history),
    }


@app.delete("/chat/{session_id}")
def delete_session(session_id: str):
    """Xóa session (user logout) khỏi Redis."""
    _redis.delete(f"history:{session_id}")
    return {"deleted": session_id}


# ──────────────────────────────────────────────────────────
# Health / Metrics
# ──────────────────────────────────────────────────────────


@app.get("/health")
def health():
    try:
        _redis.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    status = "ok" if redis_ok else "degraded"

    return {
        "status": status,
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": "redis",
        "redis_connected": redis_ok,
    }


@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    try:
        _redis.ping()
    except Exception:
        raise HTTPException(503, "Redis not available")
    return {"ready": True, "instance": INSTANCE_ID}


# Signal handlers cho SIGTERM và SIGINT
def handle_exit_signal(signum, frame):
    logger.info(f"Signal {signum} received, letting uvicorn handle graceful shutdown...")

signal.signal(signal.SIGTERM, handle_exit_signal)
signal.signal(signal.SIGINT, handle_exit_signal)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        # Cấu hình uvicorn cho graceful shutdown
        timeout_graceful_shutdown=30
    )
