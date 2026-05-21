"""An MCP server exposed over Streamable HTTP — deployable on Coffeece.

MCP (Model Context Protocol) servers give AI agents and assistants a typed set
of tools and resources. Over the Streamable HTTP transport an MCP server is
just an HTTP app: deploy it like any other web service and point an MCP client
at https://<app>.coffeece.com/mcp.

The tools and resource below are intentionally trivial — copy this file and
replace them with your own.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = FastMCP("coffeece-example-tools")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


@mcp.tool()
def word_count(text: str) -> dict:
    """Count the words and characters in a piece of text."""
    return {"words": len(text.split()), "characters": len(text)}


@mcp.resource("info://server")
def server_info() -> str:
    """Basic information about this MCP server."""
    return "coffeece-example-tools — a sample MCP server hosted on Coffeece."


@mcp.custom_route("/healthz", methods=["GET"])
async def healthz(_request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# Streamable HTTP ASGI app — MCP is served at /mcp. uvicorn runs this (see Procfile).
app = mcp.streamable_http_app()
