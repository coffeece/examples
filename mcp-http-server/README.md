# MCP Server over HTTP (Python)

An [MCP](https://modelcontextprotocol.io/) server exposed over the **Streamable
HTTP** transport — deployable on Coffeece like any other web app.

MCP (Model Context Protocol) is how AI assistants and agents discover and call
a typed set of tools and resources. Over Streamable HTTP an MCP server is just
an HTTP service: deploy it, then point any MCP client — Claude Code, Claude
Desktop, your own agent — at `https://<app>.coffeece.com/mcp`.

Built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk) from
the official Python SDK. The two tools and one resource here are deliberately
trivial — copy `server.py` and replace them with your own.

## What it exposes

| Kind | Name | What it does |
|---|---|---|
| Tool | `add` | Adds two numbers. |
| Tool | `word_count` | Counts words and characters in a string. |
| Resource | `info://server` | A short description of the server. |

## Deploy on Coffeece

```bash
# 1. Create the app
tsuru app create mcp-tools python -o shared-free

# 2. Deploy
tsuru app deploy -a mcp-tools .
```

The MCP endpoint is then live at `https://mcp-tools.coffeece.com/mcp`.
No env vars or secrets needed for this example.

## Connect a client

**Claude Code:**

```bash
claude mcp add --transport http example-tools https://mcp-tools.coffeece.com/mcp
```

Then ask Claude to use the `add` or `word_count` tool.

**MCP Inspector** (visual debugger — no install needed):

```bash
npx @modelcontextprotocol/inspector
```

Set the transport to *Streamable HTTP* and the URL to
`https://mcp-tools.coffeece.com/mcp`, then connect and browse the tools.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --port 8931
```

Verify it from another terminal:

```bash
curl -s http://localhost:8931/healthz        # -> {"status":"ok"}
```

Then connect a client to `http://localhost:8931/mcp`, or point the MCP
Inspector at that URL.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | — | Set automatically by Tsuru. |

## Notes

- **`/mcp`** speaks the MCP Streamable HTTP protocol — a plain browser GET
  won't render anything useful; use an MCP client.
- **`/healthz`** is a plain HTTP check, used by the Tsuru healthcheck
  (see `tsuru.yml`).
- The server is stateful (one session manager per process). It fits the free
  tier's single unit; if you scale to multiple units, switch FastMCP to
  stateless HTTP or add a shared session store.

## File map

```
.
├── server.py        # FastMCP server — tools, resource, /healthz
├── requirements.txt
├── Procfile         # web: uvicorn server:app --host 0.0.0.0 --port $PORT
├── tsuru.yml        # healthcheck on /healthz
└── README.md
```
