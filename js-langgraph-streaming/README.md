# Streaming Chat Agent (Node + LangGraph.js)

A streaming chat agent using
[LangGraph.js](https://github.com/langchain-ai/langgraphjs) /
[LangChain.js](https://github.com/langchain-ai/langchainjs). Tokens stream
over **Server-Sent Events** to a tiny chat UI in `public/index.html`.

Tools available to the agent:

| Tool | Purpose |
|---|---|
| `calculator` | Evaluates arithmetic expressions via [mathjs](https://mathjs.org). |
| `tavily_search` | Web search via [Tavily](https://tavily.com) (skipped if `TAVILY_API_KEY` is unset). |

## Deploy on Coffeece

```bash
tsuru app create chatbot nodejs -t <your-team> -o shared-free -p app-free-sandboxed
tsuru env-set -a chatbot \
  ANTHROPIC_API_KEY=YOUR_KEY \
  TAVILY_API_KEY=YOUR_TAVILY_KEY \
  --private
tsuru app deploy -a chatbot .
```

Open `https://chatbot.coffeece.com` — tokens should appear in the chat UI as
they're produced (not all at once at the end).

## API

### `GET /`
Serves `public/index.html`.

### `POST /chat`
Streams Server-Sent Events.

Body:
```json
{ "messages": [{ "role": "user", "content": "what is 17*19?" }] }
```

Each frame is one of:
```json
{ "type": "token", "value": "..." }
{ "type": "tool_call", "name": "calculator", "args": "{\"expression\":\"17*19\"}" }
{ "type": "done" }
{ "type": "error", "message": "..." }
```

### `GET /healthz`
Liveness check.

## Try it from curl

`curl -N` keeps the stream open and prints frames as they arrive. If you see
the entire response come at once instead of trickling, a proxy is buffering
(should not happen on Coffeece — the server sets `X-Accel-Buffering: no`).

```bash
APP=https://chatbot.coffeece.com

curl -N -X POST $APP/chat \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"what is 17*19? then briefly explain it"}]}'
```

## Run locally

```bash
npm install
export ANTHROPIC_API_KEY=...
# optional: export TAVILY_API_KEY=...
npm start
# open http://localhost:8888
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | **Required.** Anthropic API key. |
| `TAVILY_API_KEY` | — | Optional. Without it, web search is disabled but the calculator still works. |
| `ANTHROPIC_MODEL` | `claude-haiku-4-5` | Override model id. |
| `PORT` | `8888` | Set automatically by Tsuru. |

## File map

```
.
├── server.js            # Express, SSE handler, agent build
├── tools.js             # calculator + Tavily as DynamicStructuredTool
├── public/
│   └── index.html       # Chat UI; talks to /chat over fetch+SSE
├── package.json
├── .nvmrc               # node 20
├── Procfile             # web: node server.js
├── tsuru.yml            # healthcheck on /healthz
└── README.md
```
