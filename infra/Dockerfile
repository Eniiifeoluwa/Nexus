# ── Main Application Image ─────────────────────────────────────────────────────
FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        curl \
        libopenblas-dev \
        docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create runtime directories
RUN mkdir -p artifacts logs chroma_db

# Environment defaults (override via .env or docker-compose)
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000 9090

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
