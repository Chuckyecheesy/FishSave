"""
FastAPI app that:
1. Generates a spoken-friendly policy explanation using Cohere
   (via explain_policy_impact_for_elevenlabs.run), and
2. Sends that text to ElevenLabs Text-to-Speech,
   returning an audio/mpeg stream for playback in the frontend.

Run locally (example):
    uvicorn policy_tts_api:app --reload --port 8010

Then POST from the frontend to:
    POST /api/policy-explanation-audio
with JSON body:
    {
      "country": "Brazil",
      "horizon_years": 5,
      "risk_score": 0.49,
      "policies": [
        "Implement temporary seasonal fishing closures",
        "Tighten gear restrictions to reduce bycatch",
        "Strengthen local enforcement of maritime boundaries"
      ],
      "voice_id": "optional-elevenlabs-voice-id"
    }
"""

from __future__ import annotations

import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field, field_validator

from dotenv import load_dotenv
import requests
from gtts import gTTS
from io import BytesIO

from explain_policy_impact_for_elevenlabs import run as generate_policy_explanation


load_dotenv()

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "").strip()
ELEVENLABS_TTS_URL_TEMPLATE = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

if not ELEVENLABS_API_KEY:
    # We don't crash the app on import, but endpoints will return a clear error.
    print("Warning: ELEVENLABS_API_KEY not set; TTS endpoint will return 500.")


class PolicyTTSRequest(BaseModel):
    country: str = Field(..., description="Country name")
    horizon_years: int = Field(..., description="Forecast horizon in years (5 or 10)")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Overfishing risk score in [0, 1]")
    policies: List[str] = Field(..., min_items=1, max_items=3, description="One to three policy recommendations")
    voice_id: Optional[str] = Field(
        None,
        description="Optional ElevenLabs voice ID. If omitted, ELEVENLABS_VOICE_ID from the environment is used.",
    )

    @field_validator("horizon_years")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        if v not in (5, 10):
            raise ValueError("horizon_years must be 5 or 10")
        return v


class RiskTTSRequest(BaseModel):
    category: str = Field(..., description="Risk category: Low, Medium, or High")
    voice_id: Optional[str] = Field(
        None,
        description="Optional ElevenLabs voice ID.",
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v.lower() not in ("low", "medium", "high"):
            raise ValueError("category must be Low, Medium, or High")
        return v.title()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FishSave Policy TTS API")

# CORS: frontend does not send credentials, so "*" is allowed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Ensure CORS headers on error responses (some proxies/clients strip them on 5xx)
CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=CORS_HEADERS,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=CORS_HEADERS,
    )


@app.get("/")
def root():
    """Root route so the base URL returns info instead of 404."""
    return {
        "service": "FishSave Policy TTS API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "policy_audio": "POST /api/policy-explanation-audio",
            "risk_audio": "POST /api/risk-explanation-audio",
        },
    }


def _synthesize_audio_with_fallback(text: str, voice_id: str) -> bytes:
    """
    Primary: ElevenLabs TTS.
    Fallback: gTTS ONLY when ElevenLabs returns 429 (Too Many Requests).
    """
    if ELEVENLABS_API_KEY and voice_id:
        url = ELEVENLABS_TTS_URL_TEMPLATE.format(voice_id=voice_id)
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        body = {
            "model_id": "eleven_multilingual_v2",
            "text": text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=60)
            if resp.status_code == 200:
                return resp.content
            
            # Use gTTS ONLY on 429 (Too Many Requests)
            if resp.status_code == 429:
                print("ElevenLabs 429 hit. Falling back to gTTS...")
                buffer = BytesIO()
                tts = gTTS(text=text, lang="en")
                tts.write_to_fp(buffer)
                return buffer.getvalue()
            
            # For any other non-200 error, fail hard as requested
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"ElevenLabs TTS API error: {resp.text}",
            )
        except HTTPException:
            raise
        except Exception as e:
            # For network/other errors, we might want to fail too if "keep gtts off" is strict
            raise HTTPException(status_code=502, detail=f"ElevenLabs connection error: {str(e)}")

    # No API key or voice_id -> fail since user wants gTTS strictly as a 429 fallback
    raise HTTPException(status_code=500, detail="ElevenLabs credentials or voice_id not configured.")


@app.post("/api/policy-explanation-audio", response_class=Response)
def policy_explanation_audio(payload: PolicyTTSRequest) -> Response:
    """
    Generate a policy explanation for the given country/horizon/risk/policies
    and return an audio/mpeg stream (ElevenLabs primary, gTTS fallback).
    """
    voice_id = (payload.voice_id or DEFAULT_VOICE_ID).strip()

    # 1) Generate explanation text via Cohere.
    try:
        explanation_text = generate_policy_explanation(
            country=payload.country,
            horizon_years=payload.horizon_years,
            risk_score=payload.risk_score,
            policies=payload.policies,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating policy explanation: {e}",
        ) from e

    if not explanation_text:
        raise HTTPException(
            status_code=500,
            detail="No explanation text generated from Cohere.",
        )

    # 2) Synthesize audio via ElevenLabs with gTTS fallback.
    audio_bytes = _synthesize_audio_with_fallback(explanation_text, voice_id)

    # Return raw audio bytes for the frontend to play.
    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.post("/api/risk-explanation-audio", response_class=Response)
def risk_explanation_audio(payload: RiskTTSRequest) -> Response:
    """
    Generate an explanation audio for the risk category significance on fish inflation.
    """
    category = payload.category.lower()
    voice_id = (payload.voice_id or DEFAULT_VOICE_ID).strip()

    # Define the text based on the user's specific definitions
    if category == "low":
        explanation_text = (
            "The overfishing risk is currently Low. This means that overfishing has no "
            "significance on the inflation price of fish in this region."
        )
    elif category == "medium":
        explanation_text = (
            "The overfishing risk is currently Medium. This indicates a moderately "
            "significant effect of overfishing on fish price inflation."
        )
    else:  # high
        explanation_text = (
            "The overfishing risk is currently High. This signifies a definitely "
            "significant impact of overfishing on the inflation price of fish, "
            "requiring urgent policy intervention."
        )

    # Synthesize audio via ElevenLabs with gTTS fallback.
    audio_bytes = _synthesize_audio_with_fallback(explanation_text, voice_id)

    return Response(content=audio_bytes, media_type="audio/mpeg")


@app.get("/health")
def healthcheck() -> dict:
    """Simple health check endpoint."""
    return {"status": "ok"}

