"""FastAPI microservice: Persian speech-to-text with Whisper.

Auth:   Authorization: Bearer <token>  (tokens created via CLI, stored in Postgres)
File:   POST /api/v1/transcribe  (multipart `file`, optional `language`, default `fa`)
Stream: WS   /api/v1/stream?token=<token>  (binary audio chunks, send text `{"eof":true}` to finalize)
"""
import json
import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .auth import require_auth, require_auth_ws
from .config import settings
from .db import SessionLocal, init_db
from .models import ApiToken
from .schemas import TranscriptionResponse
from .whisper_service import transcribe_file


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create api_tokens table if missing
    yield


app = FastAPI(title="Persian Whisper STT", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model": settings.whisper_model_size, "default_language": settings.whisper_default_language}


@app.post("/api/v1/transcribe", response_model=TranscriptionResponse)
async def transcribe_endpoint(
    file: UploadFile = File(...),
    language: str = Query(default="fa", description="Whisper language code, default 'fa' (Persian)"),
    _token: ApiToken = Depends(require_auth),
):
    suffix = os.path.splitext(file.filename or "audio")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        if not content:
            return JSONResponse(status_code=400, content={"detail": "Empty audio file"})
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = transcribe_file(tmp_path, language=language)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return result


@app.websocket("/api/v1/stream")
async def stream_endpoint(
    websocket: WebSocket,
    language: str = Query(default="fa"),
):
    """Streaming STT over WebSocket.

    Client: connect with `?token=<api_token>`, send binary audio chunks.
    Send a text frame `{"eof": true}` (or `"finalize"`) to transcribe the
    buffered utterance; server replies with JSON transcription and clears
    the buffer so the same socket can handle the next utterance.
    """
    await websocket.accept()
    db = SessionLocal()
    try:
        rec = await require_auth_ws(websocket, db)
        if rec is None:
            await websocket.send_text(json.dumps({"error": "unauthorized"}))
            await websocket.close(code=4401)
            return

        buffer = bytearray()
        await websocket.send_text(json.dumps({"ready": True, "language": language}))

        while True:
            msg = await websocket.receive()
            if "bytes" in msg and msg["bytes"]:
                buffer.extend(msg["bytes"])
                await websocket.send_text(json.dumps({"buffered_bytes": len(buffer)}))
            elif "text" in msg and msg["text"]:
                text = msg["text"].strip()
                finalize = text.lower() in {"finalize", "eof"} or '"eof"' in text or '"finalize"' in text
                if finalize:
                    if not buffer:
                        await websocket.send_text(json.dumps({"error": "empty buffer"}))
                        continue
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
                        tmp.write(bytes(buffer))
                        tmp_path = tmp.name
                    buffer.clear()
                    try:
                        result = transcribe_file(tmp_path, language=language)
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass
                    await websocket.send_text(json.dumps(result, ensure_ascii=False))
                else:
                    await websocket.send_text(json.dumps({"echo": text}))
            elif msg.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
