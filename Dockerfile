# FishSave backend for Cloud Run (FastAPI + policy TTS API)
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code (only what the API needs)
COPY policy_tts_api.py .
COPY explain_policy_impact_for_elevenlabs.py .

# Cloud Run sets PORT at runtime (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn policy_tts_api:app --host 0.0.0.0 --port ${PORT:-8080}"]
