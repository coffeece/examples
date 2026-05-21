# Simple Chatbot (Python + Claude)

The smallest useful chatbot: a FastAPI server that forwards a conversation to
[Claude](https://www.anthropic.com/) and returns the reply. No agent framework,
no tools, no database — one Anthropic Messages API call per turn.

The server is **stateless**. The browser holds the conversation and sends the
full message history on every request. That keeps the app trivial to scale and
makes it a clean starting point to copy from.

If you want tool-calling, streaming, or stateful workflows, see the other
examples in this catalog — this one is deliberately the floor.

## Deploy on Coffeece

```bash
# 1. Create the app
tsuru app create chatbot python -o shared-free

# 2. Add your Anthropic API key
tsuru env-set -a chatbot ANTHROPIC_API_KEY=YOUR_KEY --private

# 3. Deploy
tsuru app deploy -a chatbot .
```

Open `https://chatbot.coffeece.com` and start chatting.

## API

### `GET /`
The browser chat UI.

### `POST /chat`
```json
{ "messages": [
  { "role": "user", "content": "Hello!" }
] }
```
→ runs one Claude call and returns:
```json
{ "reply": "Hi! How can I help you today?" }
```
Send the whole conversation back each turn — the server keeps no history.
Messages must start with a `user` turn.

### `GET /healthz`
Liveness check; reports the active model.

## Try it

```bash
APP=https://chatbot.coffeece.com

curl -sX POST $APP/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"Write a haiku about deploys."}]}' | jq
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
uvicorn app:app --port 8888
```

Then open <http://localhost:8888>.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Anthropic API key. |
| `ANTHROPIC_MODEL` | `claude-opus-4-7` | Model to use. Set `claude-haiku-4-5` for a cheaper, faster bot. |
| `SYSTEM_PROMPT` | *(a generic helpful-assistant prompt)* | Sets the bot's persona and behavior. |
| `MAX_TOKENS` | `1024` | Cap on reply length. |
| `PORT` | — | Set automatically by Tsuru. |

## File map

```
.
├── app.py             # FastAPI app — /chat does one Anthropic call
├── public/index.html  # Browser chat UI (vanilla JS, no build step)
├── requirements.txt
├── Procfile           # web: uvicorn app:app --host 0.0.0.0 --port $PORT
├── tsuru.yml          # healthcheck on /healthz
└── README.md
```
