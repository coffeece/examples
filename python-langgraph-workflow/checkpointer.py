"""Checkpointer selection: bound PostgreSQL when available, in-memory otherwise.

Tsuru injects DATABASE_URL when the app is bound to a `postgresql` service
instance:

    tsuru service instance bind postgresql <name> -a <app>

When that variable is set, conversations survive restarts. When it isn't,
the graph falls back to :class:`MemorySaver` and state is lost when the
container restarts.
"""

from __future__ import annotations

import os
from contextlib import AbstractContextManager
from typing import Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver


def _normalize(url: str) -> str:
    # SQLAlchemy-style "postgresql://" works; psycopg also accepts "postgres://".
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def build():
    """Return ``(checkpointer, ctx_or_none, kind)``.

    The caller (FastAPI lifespan) is responsible for entering and exiting
    ``ctx_or_none`` if it isn't ``None``.
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        cm: AbstractContextManager = PostgresSaver.from_conn_string(_normalize(db_url))
        saver = cm.__enter__()
        saver.setup()
        return saver, cm, "postgres"
    return MemorySaver(), None, "memory"
