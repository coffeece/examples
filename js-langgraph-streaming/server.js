import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ChatAnthropic } from "@langchain/anthropic";
import { createReactAgent } from "@langchain/langgraph/prebuilt";
import { HumanMessage } from "@langchain/core/messages";

import { buildTools } from "./tools.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

if (!process.env.ANTHROPIC_API_KEY) {
  console.error("ANTHROPIC_API_KEY is required");
  process.exit(1);
}

const llm = new ChatAnthropic({
  model: process.env.ANTHROPIC_MODEL ?? "claude-haiku-4-5",
  temperature: 0,
  streaming: true,
});

const agent = createReactAgent({ llm, tools: buildTools() });

const app = express();
app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "public")));

app.get("/healthz", (_req, res) => res.json({ status: "ok" }));

app.post("/chat", async (req, res) => {
  const messages = Array.isArray(req.body?.messages) ? req.body.messages : null;
  if (!messages || messages.length === 0) {
    res.status(400).json({ error: "messages array is required" });
    return;
  }

  // SSE headers — also disable proxy buffering on Tsuru's ingress-nginx.
  res.set({
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no",
  });
  res.flushHeaders?.();

  const send = (payload) => {
    res.write(`data: ${JSON.stringify(payload)}\n\n`);
  };

  const input = {
    messages: messages.map((m) => new HumanMessage({ content: m.content })),
  };

  try {
    const stream = await agent.stream(input, { streamMode: "messages" });
    for await (const [chunk, _meta] of stream) {
      // chunk is an AIMessageChunk (or ToolMessage on tool returns).
      // Tool calls show up as `tool_call_chunks` on the AIMessageChunk.
      if (chunk?.tool_call_chunks?.length) {
        for (const call of chunk.tool_call_chunks) {
          if (call?.name) {
            send({ type: "tool_call", name: call.name, args: call.args ?? "" });
          }
        }
      }

      const text = typeof chunk?.content === "string"
        ? chunk.content
        : Array.isArray(chunk?.content)
          ? chunk.content.map((c) => (typeof c === "string" ? c : c?.text ?? "")).join("")
          : "";
      if (text) send({ type: "token", value: text });
    }
    send({ type: "done" });
  } catch (err) {
    console.error("agent error", err);
    send({ type: "error", message: err?.message ?? "agent failed" });
  } finally {
    res.end();
  }
});

const port = process.env.PORT || 8888;
app.listen(port, () => {
  console.log(`agent ready on :${port}`);
});
