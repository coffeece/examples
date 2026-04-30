# Email-reply Drafter (Python + LangGraph)

A human-in-the-loop email-reply workflow built with [LangGraph](https://github.com/langchain-ai/langgraph).
The graph classifies an inbound email, drafts a reply, **pauses for human review**,
and only "sends" after explicit approval.

The interesting bit: when the app is bound to Coffeece's `postgresql` service,
the graph state is checkpointed to PostgreSQL — so paused threads survive
deploys, restarts, and crashes.

## State machine

```
        ┌────────────┐     ┌───────┐
START ─►│  classify  │ ──► │ draft │ ──► (pause: awaiting review) ──► send ──► END
        └────────────┘     └───────┘            │
                                                ├─ POST /threads/{id}/edit    (re-pauses)
                                                └─ POST /threads/{id}/approve (resumes → send)
```

## Deploy on Coffeece

```bash
# 1. Create the app
tsuru app create maildraft python -o shared-free

# 2. (Recommended) Bind a postgresql service so paused threads survive restarts
tsuru service instance add postgresql maildraft-pg db-free
tsuru service instance bind postgresql maildraft-pg -a maildraft

# 3. Add the LLM key
tsuru env-set -a maildraft ANTHROPIC_API_KEY=YOUR_KEY --private

# 4. Deploy
tsuru app deploy -a maildraft .
```

If you skip step 2, the app falls back to an in-memory checkpointer and you'll
see `checkpointer=memory` in the logs. Threads will be lost on restart.

## API

### `POST /threads`
```json
{ "inbound": "Hi, I want a refund for order 42." }
```
→ runs through `classify` and `draft`, then pauses. Returns the draft and a `thread_id`:
```json
{
  "thread_id": "ab12cd34ef56",
  "status": "awaiting_review:send",
  "inbound": "Hi, I want a refund for order 42.",
  "category": "refund",
  "draft": "Hi! Thanks for reaching out. ...",
  "approved": false,
  "sent_at": null
}
```

### `GET /threads/{thread_id}`
Returns the full state of a thread.

### `POST /threads/{thread_id}/approve`
Resumes the graph; runs the `send` node.
```json
{
  "thread_id": "ab12cd34ef56",
  "status": "sent",
  "approved": true,
  "sent_at": "2026-04-29T18:32:11.123456+00:00",
  ...
}
```

### `POST /threads/{thread_id}/edit`
```json
{ "draft": "I rewrote this myself, thanks." }
```
Overwrites the draft and re-pauses at `send`.

### `GET /healthz`
Liveness check; reports the active checkpointer kind.

## Try it

```bash
APP=https://maildraft.coffeece.com

# Start a thread
TID=$(curl -sX POST $APP/threads \
  -H 'Content-Type: application/json' \
  -d '{"inbound":"Hi, I want a refund for order 42."}' | jq -r .thread_id)

# Look at the draft
curl -s $APP/threads/$TID | jq

# *** The punchline ***
tsuru app restart -a maildraft

# Same draft is still there — the PG checkpointer kept it across the restart
curl -s $APP/threads/$TID | jq

# Approve and "send"
curl -sX POST $APP/threads/$TID/approve | jq
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
# Optional: export DATABASE_URL=postgresql://user:pass@localhost:5432/db
uvicorn app:app --port 8888
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Anthropic API key. |
| `DATABASE_URL` | — | Optional. Auto-injected by `tsuru service instance bind postgresql ... -a <app>`. When set, state is persisted; otherwise the app uses an in-memory checkpointer. |
| `PORT` | — | Set automatically by Tsuru. |

## File map

```
.
├── app.py            # FastAPI app + lifespan
├── graph.py          # StateGraph, classify/draft/send nodes
├── checkpointer.py   # PostgresSaver-or-MemorySaver selection
├── requirements.txt
├── Procfile          # web: uvicorn app:app --host 0.0.0.0 --port $PORT
├── tsuru.yml         # healthcheck on /healthz
└── README.md
```
