# Persian Whisper STT Microservice

FastAPI microservice that transcribes **spoken Persian (fa)** using the Whisper AI model
(`faster-whisper`). Supports **file upload** and **streaming voice** via WebSocket.
API access is protected by **bearer tokens** generated from the console and stored
(hashed with SHA-256) in **PostgreSQL**.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | no | Health check |
| POST | `/api/v1/transcribe` | `Bearer <token>` | Multipart `file` (+ `?language=fa`). Returns `{text, language, duration, segments}` |
| WS | `/api/v1/stream?token=<token>&language=fa` | query/header token | Send binary audio chunks, then text `{"eof":true}` to finalize; server replies with transcription JSON |

## Quickstart (Docker)

```bash
cp .env.example .env
docker compose up --build
# API -> http://localhost:8000, docs -> http://localhost:8000/docs
```

Create a token (in another terminal):

```bash
docker compose exec api python -m app.cli create-token --name my-client
# -> prints e.g. wsp_xxx  (copy it, only shown once)
```

Transcribe a file:

```bash
curl -H "Authorization: Bearer wsp_xxx" \
  -F "file=@sample_fa.mp3" \
  "http://localhost:8000/api/v1/transcribe?language=fa"
```

Streaming (Python example):

```python
import asyncio, json, websockets
async def main():
    async with websockets.connect("ws://localhost:8000/api/v1/stream?token=wsp_xxx&language=fa") as ws:
        print(await ws.recv())  # {"ready": true, ...}
        with open("sample_fa.mp3","rb") as f:
            while chunk := f.read(32000):
                await ws.send(chunk)
                print(await ws.recv())  # buffered_bytes
        await ws.send(json.dumps({"eof": True}))
        print(await ws.recv())  # transcription
asyncio.run(main())
```

## Local dev (without Docker)

Requires Python 3.11+ and PostgreSQL + ffmpeg.

```bash
pip install -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://whisper:whisperpass@localhost:5432/whisperdb
python -m app.cli create-token --name my-client
python -m app
```

## Console token commands

```bash
python -m app.cli create-token --name my-client [--quota 100]
python -m app.cli list-tokens
python -m app.cli revoke-token --name my-client
```

`--quota` sets the maximum number of allowed requests for that token. Usage is incremented automatically on every transcription request (both HTTP and WebSocket). When the quota is exceeded the server returns `429 Too Many Requests`. Omit `--quota` for unlimited access.

## Token fields (PostgreSQL `api_tokens`)

| Column       | Type          | Description                              |
|--------------|---------------|------------------------------------------|
| `name`       | `String(128)` | Client label, unique                     |
| `token_hash` | `String(64)`  | SHA-256 of the plaintext token           |
| `prefix`     | `String(16)`  | First 8 chars of token (for identification only) |
| `usage`      | `Integer`     | Number of times this token has been used |
| `quota`      | `Integer|null`| Max allowed requests, `null` = unlimited |
| `revoked`    | `Boolean`     | Whether the token is revoked             |
| `last_used_at`| `DateTime`    | Last request timestamp                   |

## Config (env)

`DATABASE_URL`, `WHISPER_MODEL_SIZE` (tiny/base/small/medium/large-v3, default `small`),
`WHISPER_DEVICE` (cpu/cuda), `WHISPER_COMPUTE_TYPE` (int8/float16),
`WHISPER_DEFAULT_LANGUAGE` (default `fa`).

For best Persian accuracy use `WHISPER_MODEL_SIZE=medium` or `large-v3` on a GPU host.
