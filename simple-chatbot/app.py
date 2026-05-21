"""A minimal stateless chatbot — one Anthropic Messages API call per turn.

The server keeps no state. The browser holds the conversation and sends the
full message history on every request; the server forwards it to Claude and
returns the reply.

Endpoints:
    GET  /          — the browser chat UI
    POST /chat      — {"messages": [{"role", "content"}, ...]} -> {"reply": ...}
    GET  /healthz   — liveness
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("simple-chatbot")

# claude-opus-4-7 is the default. Override with ANTHROPIC_MODEL — e.g.
# claude-haiku-4-5 for a cheaper, faster bot.
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "You are a helpful, friendly assistant. Keep answers concise.",
)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1024"))

_INDEX = Path(__file__).parent / "public" / "index.html"


class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., min_length=1)


if not os.environ.get("ANTHROPIC_API_KEY"):
    log.warning("ANTHROPIC_API_KEY is not set; /chat will fail until it is")

app = FastAPI(title="simple-chatbot")

# Built lazily so a missing API key doesn't crash boot — /healthz must answer
# the Tsuru healthcheck even before the key is set.
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


@app.get("/healthz")
def healthz():
    return {"status": "ok", "model": MODEL}


@app.get("/")
def index():
    return FileResponse(_INDEX)


@app.post("/chat")
def chat(body: ChatRequest):
    if body.messages[0].role != "user":
        raise HTTPException(400, "conversation must start with a user message")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(503, "ANTHROPIC_API_KEY is not configured")
    try:
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[m.model_dump() for m in body.messages],
            # Auto-caches the conversation prefix; pays off once the history
            # crosses the model's minimum cacheable size on later turns.
            cache_control={"type": "ephemeral"},
        )
    except anthropic.APIStatusError as e:
        log.error("anthropic error: %s", e)
        raise HTTPException(502, f"LLM request failed: {e.message}") from e

    reply = next((b.text for b in response.content if b.type == "text"), "")
    return {"reply": reply}
