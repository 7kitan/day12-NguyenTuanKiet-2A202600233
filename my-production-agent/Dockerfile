# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Final Runtime
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

WORKDIR /app

# Non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app

# Copy deps
COPY --from=builder /root/.local /home/appuser/.local

# Copy code
COPY app/ ./app/
COPY utils/ ./utils/

# Proper ownership
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Health check (using python to avoid curl dependency)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --timeout-graceful-shutdown 30
