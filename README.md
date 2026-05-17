# Coffeece Examples

Reference apps you can deploy as-is to [Coffeece](https://coffeece.com) — a
managed [Tsuru](https://tsuru.io) PaaS — to see what's possible on the platform
and to copy as a starting point for your own apps.

Each example is a self-contained app with a `Procfile`, `tsuru.yml`, and a
README that walks through deploy and usage.

## Examples

So far the catalog is focused on **AI agents** — a common ask we wanted
working templates for. More examples (plain web apps, cron jobs, background
workers, full-stack with managed Postgres) will land here over time.

| Example | Stack | What it shows |
|---|---|---|
| [go-adk-multiagent](./go-adk-multiagent) | Go · [ADK](https://github.com/google/adk-go) · Gemini | Help-desk coordinator that delegates to billing / technical / escalation sub-agents via `transfer_to_agent`. |
| [js-langgraph-streaming](./js-langgraph-streaming) | Node · [LangGraph.js](https://github.com/langchain-ai/langgraphjs) · Claude | SSE chat agent that streams tokens to a tiny browser UI; tools include a calculator and Tavily web search. |
| [python-langgraph-workflow](./python-langgraph-workflow) | Python · [LangGraph](https://github.com/langchain-ai/langgraph) · Claude | Human-in-the-loop email-reply drafter; graph state is checkpointed to a bound `postgresql` service so paused threads survive restarts. |

## Deploying any example

The flow is the same for every app — see the example's README for the exact
env vars and any service bindings it needs.

```bash
# 1. Pick a platform: go | nodejs | python | static
tsuru app create <name> <platform> -o shared-free

# 2. Set secrets / config
tsuru env-set -a <name> SOME_API_KEY=... --private

# 3. (Optional) Bind a managed Postgres if the example uses it
tsuru service instance add postgresql <name>-pg db-free
tsuru service instance bind   postgresql <name>-pg -a <name>

# 4. Deploy from the example directory
cd <example-dir>
tsuru app deploy -a <name> .
```

The app lands at `https://<name>-<org>.app.coffeece.com`. Tail logs with
.
`tsuru app log -a <name> -f`.

New to Coffeece? Sign up at <https://coffeece.com> — the free tier
fits each of these examples.

## Contributing

PRs welcome. A good example is:

- **Self-contained** — one directory, no shared scaffolding.
- **Runnable locally** with a short `Run locally` section in its README.
- **Deployable as documented** — the `tsuru app create … && tsuru app deploy`
  block in the README actually works end-to-end on a fresh app.
- **Honest about limits** — call out what's faked, in-memory, or skipped so
  someone adapting the template knows what to replace.
