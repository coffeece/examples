"""FastAPI server that exposes the email-reply workflow.

Endpoints:
    POST /threads             — start a new thread, run until the interrupt
    GET  /threads/{id}        — fetch the current state from the checkpointer
    POST /threads/{id}/approve — resume the graph (executes "send")
    POST /threads/{id}/edit    — overwrite the draft and pause again
    GET  /healthz              — liveness
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import checkpointer as cp
from graph import build_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("maildraft")


class CreateThreadRequest(BaseModel):
    inbound: str = Field(..., min_length=1)


class EditDraftRequest(BaseModel):
    draft: str = Field(..., min_length=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    saver, ctx, kind = cp.build()
    log.info("checkpointer=%s", kind)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("ANTHROPIC_API_KEY is not set; LLM calls will fail")
    app.state.graph = build_graph(saver)
    app.state.kind = kind
    try:
        yield
    finally:
        if ctx is not None:
            ctx.__exit__(None, None, None)


app = FastAPI(title="email-reply-drafter", lifespan=lifespan)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _state_snapshot(thread_id: str) -> dict:
    snap = app.state.graph.get_state(_config(thread_id))
    if snap is None or not snap.values:
        raise HTTPException(404, f"thread {thread_id} not found")
    next_nodes = list(snap.next or [])
    if not next_nodes:
        status = "sent" if snap.values.get("sent_at") else "done"
    else:
        status = f"awaiting_review:{next_nodes[0]}"
    return {
        "thread_id": thread_id,
        "status": status,
        **snap.values,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok", "checkpointer": app.state.kind}


@app.post("/threads")
def create_thread(body: CreateThreadRequest):
    thread_id = uuid.uuid4().hex[:12]
    cfg = _config(thread_id)
    # Run until the interrupt_before=["send"] gate.
    app.state.graph.invoke({"inbound": body.inbound, "approved": False, "sent_at": None}, cfg)
    return _state_snapshot(thread_id)


@app.get("/threads/{thread_id}")
def get_thread(thread_id: str):
    return _state_snapshot(thread_id)


@app.post("/threads/{thread_id}/approve")
def approve(thread_id: str):
    cfg = _config(thread_id)
    snap = app.state.graph.get_state(cfg)
    if snap is None or not snap.values:
        raise HTTPException(404, f"thread {thread_id} not found")
    if not snap.next:
        raise HTTPException(409, "thread is already complete")
    # Resume from the interrupt — `None` means "keep state, run next node".
    app.state.graph.invoke(None, cfg)
    return _state_snapshot(thread_id)


@app.post("/threads/{thread_id}/edit")
def edit(thread_id: str, body: EditDraftRequest):
    cfg = _config(thread_id)
    snap = app.state.graph.get_state(cfg)
    if snap is None or not snap.values:
        raise HTTPException(404, f"thread {thread_id} not found")
    # Update the checkpoint with the human-edited draft, keeping the same "next" node.
    app.state.graph.update_state(cfg, {"draft": body.draft})
    return _state_snapshot(thread_id)
