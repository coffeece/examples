"""Email-reply drafting workflow.

State machine:

    classify ─► draft ─► (interrupt before "send") ─► send

The graph pauses at ``send`` so a human can review/edit the draft before
it is "sent". Resuming with ``Command(resume=...)`` (via the FastAPI
``/approve`` and ``/edit`` routes) advances the graph through the
remaining nodes.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

VALID_CATEGORIES = ("refund", "technical", "sales", "spam", "other")


class State(TypedDict):
    inbound: str
    category: str
    draft: str
    approved: bool
    sent_at: Optional[str]


def _llm() -> ChatAnthropic:
    return ChatAnthropic(model="claude-haiku-4-5", temperature=0)


def classify_node(state: State) -> dict:
    sys = SystemMessage(
        content=(
            "Classify the inbound email into exactly one of: "
            f"{', '.join(VALID_CATEGORIES)}. Respond with the single word, no punctuation."
        )
    )
    msg = HumanMessage(content=state["inbound"])
    out = _llm().invoke([sys, msg]).content.strip().lower()
    if out not in VALID_CATEGORIES:
        out = "other"
    return {"category": out}


def draft_node(state: State) -> dict:
    sys = SystemMessage(
        content=(
            "You are a polite customer-support agent. Write a short, helpful reply "
            "to the inbound email. Keep it under 120 words. Do not include a subject line "
            "or signature."
        )
    )
    msg = HumanMessage(
        content=f"Category: {state['category']}\n\nInbound:\n{state['inbound']}"
    )
    reply = _llm().invoke([sys, msg]).content.strip()
    return {"draft": reply}


def send_node(state: State) -> dict:
    # In a real app this would call SMTP / SES / etc.
    return {
        "approved": True,
        "sent_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def build_graph(checkpointer):
    workflow = StateGraph(State)
    workflow.add_node("classify", classify_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("send", send_node)

    workflow.add_edge(START, "classify")
    workflow.add_edge("classify", "draft")
    workflow.add_edge("draft", "send")
    workflow.add_edge("send", END)

    # Pause so a human can review or edit the draft before "sending".
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["send"])
