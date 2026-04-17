# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /build

# Copy only requirements to leverage cache
COPY 05-scaling-reliability/production/requirements.txt .

# Install dependencies to a temporary folder
RUN pip install --no-cache-dir --user -r requirements.txt


# Stage 2: Final Runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Create non-root user for security
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app

# Copy installed dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application files and utils
# Note: Source paths are relative to the build context (repo root)
COPY 05-scaling-reliability/production/app.py .
COPY utils/ ./utils/

# Ensure proper ownership
RUN chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Start application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
