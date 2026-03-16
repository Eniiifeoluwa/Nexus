FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements_railway.txt .
RUN pip install --no-cache-dir -r requirements_railway.txt

COPY . .
RUN mkdir -p artifacts logs chroma_db

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
