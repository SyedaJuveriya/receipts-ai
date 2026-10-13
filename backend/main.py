
import asyncio
import hmac
import logging
import os
from typing import Any
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"), override=True)

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.memories import (
    LyzrExtractRequest,
    extract_memories_with_lyzr,
    router as memories_router,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RECEIPTS AI",
    description="A voice-first persistent memory agent for commitments, decisions, and changes.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://receipts-ai-six.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memories_router)


# Omi transcript buffering
omi_buffers: dict[str, str] = {}
omi_flush_tasks: dict[str, asyncio.Task] = {}
omi_buffer_lock = asyncio.Lock()
OMI_SILENCE_SECONDS = 2.5


@app.get("/")
async def root():
    return {
        "name": "RECEIPTS AI",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


def extract_omi_text(payload: Any) -> str:
    """Extract readable transcript text from common Omi webhook payloads."""

    if isinstance(payload, str):
        return payload.strip()

    if isinstance(payload, list):
        parts = [
            extract_omi_text(item)
            for item in payload
        ]
        return " ".join(part for part in parts if part).strip()

    if not isinstance(payload, dict):
        return ""

    # Common transcript text fields
    for key in ("text", "transcript", "transcription"):
        value = payload.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    # Transcript segments may contain dictionaries or strings
    for key in ("transcript_segments", "segments"):
        value = payload.get(key)

        if isinstance(value, list):
            parts = []

            for segment in value:
                if isinstance(segment, str):
                    text = segment.strip()
                elif isinstance(segment, dict):
                    text = str(segment.get("text", "")).strip()
                else:
                    text = ""

                if text:
                    parts.append(text)

            if parts:
                return " ".join(parts).strip()

    # Some Omi payloads put the transcript under structured data
    structured = payload.get("structured")

    if isinstance(structured, dict):
        for key in ("overview", "text", "transcript"):
            value = structured.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


async def process_omi_transcript(transcript: str) -> None:
    """Send a completed Omi transcript through the existing Lyzr extraction flow."""

    if not transcript.strip():
        return

    try:
        request_data = LyzrExtractRequest(message=transcript)
        await extract_memories_with_lyzr(request_data)

        logger.info("Omi transcript processed successfully.")

    except Exception:
        logger.exception("Failed to process Omi transcript.")


async def flush_omi_buffer(session_key: str) -> None:
    """Wait for a short silence, then process the buffered transcript."""

    try:
        await asyncio.sleep(OMI_SILENCE_SECONDS)

        async with omi_buffer_lock:
            transcript = omi_buffers.pop(session_key, "")
            omi_flush_tasks.pop(session_key, None)

        if transcript.strip():
            await process_omi_transcript(transcript)

    except asyncio.CancelledError:
        # A newer transcript segment arrived before the silence window ended.
        raise

    except Exception:
        logger.exception("Failed while flushing an Omi transcript buffer.")


@app.post("/omi/{token}")
async def omi_webhook(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    uid: str = "unknown",
    session_id: str | None = None,
):
    """
    Receive Omi webhook events.

    Configure the Omi webhook URL as:
    https://YOUR_PUBLIC_BACKEND_URL/omi/YOUR_WEBHOOK_SECRET

    This endpoint supports JSON objects and JSON lists.
    """

    expected_secret = os.getenv("OMI_WEBHOOK_SECRET", "").strip()

    if not expected_secret:
        logger.error("OMI_WEBHOOK_SECRET is not configured.")
        raise HTTPException(
            status_code=500,
            detail="Omi webhook secret is not configured.",
        )

    if not hmac.compare_digest(token, expected_secret):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook token.",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Request body must contain valid JSON.",
        )

    if not isinstance(payload, (dict, list)):
        raise HTTPException(
            status_code=400,
            detail="Expected a JSON object or list.",
        )

    transcript = extract_omi_text(payload)

    if not transcript:
        return {
            "status": "ignored",
            "reason": "No transcript text found in the payload.",
        }

    # Finished events can be processed immediately in the background.
    event_type = ""

    if isinstance(payload, dict):
        event_type = str(
            payload.get("type")
            or payload.get("event_type")
            or payload.get("event")
            or ""
        ).lower()

    is_finished = any(
        marker in event_type
        for marker in ("completed", "finished", "ended")
    )

    if is_finished:
        session_key = session_id or uid

        async with omi_buffer_lock:
            previous_task = omi_flush_tasks.pop(session_key, None)

            if previous_task and not previous_task.done():
                previous_task.cancel()

            previous_text = omi_buffers.pop(session_key, "")
        
        if previous_text:
            transcript = f"{previous_text} {transcript}".strip()

        background_tasks.add_task(process_omi_transcript, transcript)

        return {
            "status": "accepted",
            "event": "finished",
            "characters": len(transcript),
        }

    # Buffer live transcript segments until the speaker pauses.
    session_key = session_id or uid

    async with omi_buffer_lock:
        existing_text = omi_buffers.get(session_key, "")

        if transcript != existing_text and not existing_text.endswith(transcript):
            omi_buffers[session_key] = (
                f"{existing_text} {transcript}".strip()
                if existing_text
                else transcript
            )

        previous_task = omi_flush_tasks.get(session_key)

        if previous_task and not previous_task.done():
            previous_task.cancel()

        omi_flush_tasks[session_key] = asyncio.create_task(
            flush_omi_buffer(session_key)
        )

    return {
        "status": "accepted",
        "event": "buffered",
        "characters": len(transcript),
    }
