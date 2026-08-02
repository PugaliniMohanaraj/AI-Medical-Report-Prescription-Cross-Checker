# FastAPI application for Medical Report Cross-Checker
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/requirements-ai.txt /app/backend/requirements-ai.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-ai.txt

COPY backend /app/backend

RUN mkdir -p /app/backend/uploads /app/backend/data/chroma

EXPOSE 8000

WORKDIR /app

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
