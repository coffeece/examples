# Help-desk Multi-Agent (Go + ADK)

A help-desk coordinator built with [Google ADK for Go](https://github.com/google/adk-go).
The coordinator agent triages each incoming message and delegates to one of three
specialist sub-agents:

| Sub-agent | Tool | Responsibility |
|---|---|---|
| `billing` | `lookup_invoice(customer_id)` | Invoices, refunds, payments |
| `technical` | `check_service_status(service)` | Outage / status questions |
| `escalation` | `create_ticket(summary, priority)` | Human handoff when nothing else fits |

Sessions are kept in-memory (the demo loses them on restart — see _Limitations_).

## Architecture

```
   POST /chat ──► coordinator (LLM)
                  │
                  └─ transfer_to_agent ─► billing ──► lookup_invoice
                                       └► technical ─► check_service_status
                                       └► escalation ─► create_ticket
```

ADK's `transfer_to_agent` mechanic is built-in: when the parent agent's prompt
mentions a sub-agent name, the framework routes the next turn there
automatically.

## Deploy on Coffeece

```bash
tsuru app create helpdesk go -t <your-team> -o shared-free -p app-free-sandboxed
tsuru env-set -a helpdesk AGENT_GEMINI_API_KEY=YOUR_KEY --private
tsuru app deploy -a helpdesk .
```

Get a Gemini API key from <https://aistudio.google.com/apikey> (free tier works).

## Configuration

All env vars are prefixed with `AGENT_`:

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_GEMINI_API_KEY` | — | **Required.** Gemini API key. |
| `AGENT_GEMINI_MODEL` | `gemini-2.5-flash` | Model id. |
| `AGENT_APP_NAME` | `helpdesk` | App name passed to ADK runner. |
| `PORT` | `8888` | Set automatically by Tsuru. |

## API

### `POST /chat`

Body:
```json
{
  "session_id": "s1",
  "user_id": "u1",
  "message": "my invoice 1234 looks wrong"
}
```

Response:
```json
{
  "reply": "Your invoice 1234 is paid (R$ 199.90). ...",
  "agent": "billing"
}
```

`session_id` and `user_id` are optional; if omitted the server generates a session id and uses `anon` for the user.

### `GET /healthz`

Returns `200 OK` with body `ok` — used as the Tsuru health check.

## Try it

```bash
APP=https://helpdesk.coffeece.com

curl -sX POST $APP/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"s1","message":"my invoice 1234 looks wrong"}' | jq

curl -sX POST $APP/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"s1","message":"is the database down?"}' | jq

curl -sX POST $APP/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"s1","message":"this is unacceptable, get me a human"}' | jq
```

The `agent` field shows which specialist handled the turn — `billing`,
`technical`, or `escalation`.

## Run locally

```bash
export AGENT_GEMINI_API_KEY=YOUR_KEY
go run .
# server on :8888
```

## Limitations

- Sessions are stored in `session.InMemoryService()`. Restarting the app loses
  conversation history. For production, swap in a persistent
  `session.Service` implementation (e.g. backed by the bound `postgresql`
  service).
- Tool data is hard-coded (`fakeInvoices`, `fakeStatus`) — replace with real
  backends when adapting this template.
- ADK Go is currently labeled experimental. The pinned version is
  `google.golang.org/adk v1.2.0`.

## File map

```
.
├── main.go      # HTTP server, runner setup, /chat handler
├── agents.go    # Coordinator + 3 sub-agents
├── tools.go     # Stub implementations of the three tools
├── go.mod
├── Procfile     # web: /home/application/bin/go-adk-multiagent
├── tsuru.yml    # healthcheck on /healthz
└── README.md
```
