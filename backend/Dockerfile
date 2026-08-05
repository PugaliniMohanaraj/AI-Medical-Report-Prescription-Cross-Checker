# FastAPI application for Medical Report Cross-Checker
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# OpenCV / RapidOCR + Tesseract system deps (required for JPEG/PNG OCR on Render)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && (test -d /usr/share/tesseract-ocr/5/tessdata \
        || ln -s /usr/share/tesseract-ocr/*/tessdata /usr/share/tesseract-ocr/5/tessdata \
        || true)

COPY backend/requirements.txt /app/backend/requirements.txt
COPY backend/requirements-ai.txt /app/backend/requirements-ai.txt
RUN pip install --no-cache-dir -r /app/backend/requirements-ai.txt \
    && pip install --no-cache-dir "opencv-python-headless>=4.8.0"

COPY backend /app/backend

RUN mkdir -p /app/backend/uploads /app/backend/data/chroma

EXPOSE 8000

WORKDIR /app

# Render injects $PORT; default 8000 for local Docker
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
