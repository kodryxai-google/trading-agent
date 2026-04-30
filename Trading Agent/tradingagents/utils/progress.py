"""Real-time progress tracking for the multi-agent pipeline."""
from __future__ import annotations

import queue
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

# Map LangGraph node names → human labels + icons
_NODE_META: dict[str, tuple[str, str, str]] = {
    # node_name: (icon, label, description)
    "market_analyst":        ("📊", "Market Analyst",        "Technical analysis — price action, MA, RSI, MACD"),
    "social_media_analyst":  ("💬", "Social Analyst",        "Sentiment — Reddit, news tone, retail mood"),
    "news_analyst":          ("📰", "News Analyst",          "Macro events, FII/DII flows, sector catalysts"),
    "fundamentals_analyst":  ("🏦", "Fundamentals Analyst",  "P/E, revenue, margins, balance sheet health"),
    "bull_researcher":       ("🐂", "Bull Researcher",       "Building the upside investment case"),
    "bear_researcher":       ("🐻", "Bear Researcher",       "Building the risk and downside case"),
    "research_manager":      ("🧠", "Research Manager",      "Synthesising bull vs. bear debate"),
    "trader":                ("💼", "Trader",                "Forming investment proposal + confidence score"),
    "risky_analyst":         ("⚡", "Risk — Aggressive",     "Aggressive risk perspective"),
    "safe_analyst":          ("🛡️", "Risk — Conservative",   "Conservative risk perspective"),
    "neutral_analyst":       ("⚖️", "Risk — Neutral",        "Balanced risk assessment"),
    "risk_manager":          ("🎯", "Risk Manager",          "Final risk adjudication"),
    "portfolio_manager":     ("👔", "Portfolio Manager",     "Final BUY / SELL / HOLD decision"),
    # tool nodes
    "market_tools":          ("🔧", "Market Data Tools",     "Fetching OHLCV + technical indicators"),
    "social_tools":          ("🔧", "Social Data Tools",     "Fetching news + sentiment data"),
    "news_tools":            ("🔧", "News Data Tools",       "Fetching macro + insider data"),
    "fundamentals_tools":    ("🔧", "Fundamentals Tools",    "Fetching financial statements"),
}

_PIPELINE_ORDER = [
    "market_analyst", "market_tools",
    "social_media_analyst", "social_tools",
    "news_analyst", "news_tools",
    "fundamentals_analyst", "fundamentals_tools",
    "bull_researcher", "bear_researcher", "research_manager",
    "trader",
    "risky_analyst", "safe_analyst", "neutral_analyst", "risk_manager",
    "portfolio_manager",
]


@dataclass
class ProgressEvent:
    node: str
    icon: str
    label: str
    description: str
    status: str          # "running" | "done" | "error"
    elapsed: float = 0.0
    snippet: str = ""    # first 200 chars of agent output
    ts: float = field(default_factory=time.time)


class ProgressEmitter:
    """Thread-safe emitter. Producer calls emit(); consumer calls drain()."""

    def __init__(self):
        self._q: queue.Queue[ProgressEvent] = queue.Queue()
        self._start: dict[str, float] = {}

    def emit_start(self, node: str):
        icon, label, desc = _NODE_META.get(node, ("⚙️", node, ""))
        self._start[node] = time.time()
        self._q.put(ProgressEvent(
            node=node, icon=icon, label=label, description=desc,
            status="running",
        ))

    def emit_done(self, node: str, snippet: str = ""):
        icon, label, desc = _NODE_META.get(node, ("⚙️", node, ""))
        elapsed = time.time() - self._start.get(node, time.time())
        self._q.put(ProgressEvent(
            node=node, icon=icon, label=label, description=desc,
            status="done", elapsed=elapsed,
            snippet=snippet[:200] if snippet else "",
        ))

    def emit_error(self, node: str, error: str = ""):
        icon, label, desc = _NODE_META.get(node, ("⚙️", node, ""))
        self._q.put(ProgressEvent(
            node=node, icon=icon, label=label, description=desc,
            status="error", snippet=error[:200],
        ))

    def drain(self) -> list[ProgressEvent]:
        events = []
        while not self._q.empty():
            try:
                events.append(self._q.get_nowait())
            except queue.Empty:
                break
        return events

    def get_pipeline_order(self) -> list[str]:
        return _PIPELINE_ORDER
