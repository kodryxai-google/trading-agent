# India Trading Agent — Design Spec
Date: 2026-04-29

## Overview

Adapt the TradingAgents multi-agent framework for Indian stock market analysis, starting with TCS (TCS.NS on NSE). Uses a free data stack (yfinance + Google News RSS + BSE India API), clod.io as the LLM provider (DeepSeek V4 Pro), and outputs a Kodryx-branded HTML report with a final BUY/HOLD/SELL signal.

---

## Architecture

### Three layers

**1. Data Layer** — new modules in `tradingagents/dataflows/`

| Module | Source | Data |
|--------|--------|------|
| `y_finance.py` (existing) | Yahoo Finance | OHLCV, fundamentals, balance sheet, income statement, cashflow, insider transactions |
| `india_news.py` (new) | Google News RSS | Stock-specific news (`TCS NSE India`) + India macro news (RBI, Nifty, Sensex, rupee) |
| `india_bse.py` (new) | BSE India public API | Corporate announcements for a given BSE scrip code |
| `india_report.py` (new) | — | Renders Kodryx-styled HTML report from agent output |

`interface.py` gains an `india` vendor entry that routes news and announcement calls to the new modules. yfinance remains the vendor for price/fundamentals/technical data.

**2. LLM Layer** — clod.io wired via the existing `openrouter` path in `openai_client.py`

```
provider = "openrouter"
base_url = "https://api.clod.io/v1"
api_key  = CLODIO_API_KEY  (from .env)
deep_think_llm  = "deepseek-ai/DeepSeek-V4-Pro"
quick_think_llm = "deepseek-ai/DeepSeek-V4-Pro"
```

No changes to the LLM factory or client code — just config.

**3. Output Layer** — `india_report.py` generates `report.html` after the graph run completes

---

## Data Sources

| Category | Source | Ticker format |
|----------|--------|---------------|
| Price / OHLCV | yfinance | `TCS.NS` (NSE suffix) |
| Fundamentals | yfinance | `TCS.NS` |
| Technical indicators | yfinance + stockstats | `TCS.NS` |
| Stock news | Google News RSS | query: `"TCS NSE India"` |
| India macro news | Google News RSS | queries: `"RBI interest rate"`, `"Nifty Sensex"`, `"India inflation"`, `"rupee dollar"` |
| Corporate announcements | BSE India API | BSE scrip code (e.g. `532540` for TCS) |
| Insider transactions | yfinance | `TCS.NS` |

---

## Files

### New files

| File | Purpose |
|------|---------|
| `tradingagents/dataflows/india_news.py` | Google News RSS fetcher — stock news + macro news |
| `tradingagents/dataflows/india_bse.py` | BSE corporate announcements fetcher |
| `tradingagents/dataflows/india_report.py` | Kodryx-branded HTML report generator |
| `run_india.py` | Entry point: `python run_india.py --ticker TCS` |
| `.env` | clod.io API key, BSE scrip code map |

### Modified files

| File | Change |
|------|--------|
| `tradingagents/dataflows/interface.py` | Add `india` vendor to `VENDOR_METHODS` for `get_news` and `get_global_news` |
| `tradingagents/dataflows/__init__.py` | Export new modules |

### Untouched

All agent files, graph files, LLM clients, CLI — no changes.

---

## HTML Report Structure

Generated at `reports/TCS_YYYYMMDD_HHMMSS.html`. Self-contained (inline CSS, no external dependencies except Google Fonts CDN).

```
Header
  Kodryx logo (top-left)
  "India Trading Agent" (top-right, eyebrow)

Hero
  Eyebrow: "TCS.NS · NSE · {date}"
  H1: "Tata Consultancy Services"
  Signal badge: BUY / HOLD / SELL  (navy bg, gold text)
  Confidence score: e.g. "72% Confidence"

Metrics bar (4 cards, gold numbers)
  Current Market Price | P/E Ratio | 52-Week High | 52-Week Low

Analysis cards (one per agent)
  Fundamental Analysis
  Technical Analysis
  News & Sentiment
  BSE Announcements
  Bull Researcher
  Bear Researcher
  Risk Assessment

Final Recommendation (featured card, gold top-rule)
  Full reasoning text from portfolio manager
  Signal repeated: BUY / HOLD / SELL
```

Kodryx design tokens applied throughout:
- Colors: `#0E2A3A` navy, `#C9A24D` gold, `#FFFFFF` white
- Fonts: Poppins (headings), Inter (body) via Google Fonts
- Cards: `1px solid #EEF0F3` border, `8px` radius, no shadow
- Metrics: Poppins 700, gold color
- Eyebrows: Inter 600, uppercase, tracked `0.08em`

---

## Entry Point

```bash
python run_india.py --ticker TCS --date 2026-04-29
```

Output:
- Terminal: agent debate progress
- File: `reports/TCS_20260429_HHMMSS.html`

---

## BSE Scrip Code Map

A small hardcoded dict in `.env` / config for common stocks:

```
TCS      → 532540
RELIANCE → 500325
INFY     → 500209
HDFCBANK → 500180
WIPRO    → 507685
```

Extendable. If a scrip code is not found, BSE announcements section shows "Not available" gracefully.

---

## Constraints

- Research only — no live trading, no order placement
- No paid APIs — 100% free data sources
- Report is static HTML — no server, no database
- clod.io API key stored in `.env`, never hardcoded
