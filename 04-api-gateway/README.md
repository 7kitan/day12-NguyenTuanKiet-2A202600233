# Section 4 — API Gateway & Security

## Mục tiêu học
- Hiểu tại sao cần lớp bảo vệ trước agent
- Implement API Key authentication
- Implement JWT authentication (nâng cao)
- Rate limiting và cost protection

---

## Ví dụ Basic — API Key Authentication

```
develop/
├── app.py              # Agent với API Key auth
├── test_auth.py        # Test script
└── requirements.txt
```

### Chạy thử
```bash
cd basic
pip install -r requirements.txt
AGENT_API_KEY=my-secret-key python app.py

# Test với key hợp lệ
# curl -H "X-API-Key: my-secret-key" http://localhost:8000/ask \
#      -X POST -H "Content-Type: application/json" \
#      -d '{"question": "hello"}'

curl -H "X-API-Key: my-secret-key" \
"http://localhost:8000/ask?question=hello" \
-X POST

{"question":"hello","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé."}%             

# Test không có key → 401
curl http://localhost:8000/ask -X POST \
     -H "Content-Type: application/json" \
     -d '{"question": "hello"}'

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}%                                                                                            

```

---

## Ví dụ Advanced — JWT + Rate Limiting + Cost Guard

```
production/
├── app.py              # Full security stack
├── auth.py             # JWT token logic
├── rate_limiter.py     # In-memory rate limiter
├── cost_guard.py       # Token budget và spending alerts
├── test_advanced.py    # Test suite
└── requirements.txt
```

### Chạy thử
```bash
cd advanced
pip install -r requirements.txt
python app.py

-->
=== Demo credentials ===
  student / demo123  (10 req/min, $1/day budget)
  teacher / teach456 (100 req/min, $1/day budget)

Docs: http://localhost:8000/docs

# Lấy JWT token
curl -X POST http://localhost:8000/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username": "student", "password": "demo123"}'
     
-->
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0MTk3MjMsImV4cCI6MTc3NjQyMzMyM30.V0TvtK1u21xYyY3COCwlCKlM-CMjmU7C55E6UGYFKMw","token_type":"bearer","expires_in_minutes":60,"hint":"Include in header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."}%


# Dùng token
# curl -H "Authorization: Bearer <token>" \
#      http://localhost:8000/ask \
#      -X POST -H "Content-Type: application/json" \
#      -d '{"question": "what is docker?"}'
     
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3NzY0MTk3OTYsImV4cCI6MTc3NjQyMzM5Nn0.dWmvtwtf8BZNuaJqsPhnw5sqZoumHF_VE3WBr4qMyEs" \
     http://localhost:8000/ask \
     -X POST -H "Content-Type: application/json" \
     -d '{"question": "what is docker?"}'

{"question":"what is docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}%        

# Test rate limit: spam 20 requests liên tiếp
python test_advanced.py --test rate-limit
```

---

## Luồng bảo vệ

```
Request
  → Auth Check (401 nếu fail)
  → Rate Limit (429 nếu vượt quota)
  → Input Validation (422 nếu invalid)
  → Cost Check (402 nếu hết budget)
  → Agent (200 nếu mọi thứ OK)
```

---

## Câu hỏi thảo luận

1. Khi nào nên dùng API Key vs JWT vs OAuth2?
2. Rate limit nên đặt bao nhiêu request/phút cho một AI agent?
3. Nếu API key bị lộ, bạn phát hiện và xử lý như thế nào?
