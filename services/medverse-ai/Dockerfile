# Slim Dockerfile for the MedVerse AI service on Hugging Face Spaces.
# Builds in ~5–8 min on HF's CPU basic tier, runs in ~600 MB RAM idle
# (well under the 16 GB free ceiling).

FROM python:3.11-slim

# OS deps — build-essential is needed for sentence-transformers' tokenizer
# wheels on python 3.11.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libssl-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first so layer cache survives src/ edits.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# App code + bundled data (rare-disease KB used by complex-diagnosis).
COPY app.py .
COPY src/ ./src/
COPY data/ ./data/

# HF Spaces convention: container exposes 7860, app listens on $PORT.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
