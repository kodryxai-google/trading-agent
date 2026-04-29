# India Trading Agent — Design Spec
Date: 2026-04-29
Updated: 2026-04-29 (added Reddit, FII/DII, multi-RSS, BSE bulk deals, promoter holding, earnings alert)

## Overview

Adapt the TradingAgents multi-agent framework for Indian stock market analysis, starting with TCS (TCS.NS on NSE). Uses a 100% free data stack, clod.io as the LLM provider (DeepSeek V4 Pro), and outputs a Kodryx-branded HTML report with a final BUY/HOLD/SELL signal.

---

## Architecture

### Three layers

**1. Data Layer** — new modules in `tradingagents/dataflows/`

| Module | Source | Data |
|--------|--------|------|
| `y_finance.py` (existing) | Yahoo Finance | OHLCV, fundamentals, balance sheet, income statement, cashflow, insider transactions, promoter/institutional holdings, earnings dates |
| `india_news.py` (new) | ET Markets RSS + Google News RSS | Stock-specific + India macro news |
| `india_bse.py` (new) | BSE India public API | Corporate announcements + bulk/block deals |
| `india_fii_dii.py` (new) | NSE daily CSV | FII / DII net buy/sell activity |
| `india_reddit.py` (new) | Reddit API via PRAW | r/IndiaInvestments + r/IndianStockMarket posts |
| `india_report.py` (new) | — | Kodryx-styled HTML report generator |

`interface.py` gains an `india` vendor that routes news, social, and announcement calls to the new modules. yfinance remains vendor for price/fundamentals/technical data.

**2. LLM Layer** — clod.io wired via the existing `openrouter` path in `openai_client.py`

```
provider  = "openrouter"
base_url  = "https://api.clod.io/v1"
api_key   = CLODIO_API_KEY  (from .env)
deep_think_llm  = "deepseek-ai/DeepSeek-V4-Pro"
quick_think_llm = "deepseek-ai/DeepSeek-V4-Pro"
```

No changes to the LLM factory or client code — just config.

**3. Output Layer** — `india_report.py` generates `reports/TCS_YYYYMMDD_HHMMSS.html` after the graph run completes.

---

## Complete Data Stack

| Category | Source | Free? | Notes |
|----------|--------|-------|-------|
| Price / OHLCV | yfinance `.NS` | Yes | 15-min delay |
| Fundamentals (P/E, EPS, revenue…) | yfinance `.NS` | Yes | |
| Technical indicators | yfinance + stockstats | Yes | MACD, RSI, Bollinger, ATR, etc. |
| Promoter / institutional holding | yfinance `.NS` | Yes | `major_holders`, `institutional_holders` |
| Earnings date alert | yfinance `.NS` | Yes | Warns if results due within 14 days |
| Stock news | ET Markets RSS + Google News RSS | Yes | Multiple sources for richer coverage |
| India macro news | Google News RSS | Yes | RBI, Nifty, Sensex, rupee/dollar |
| BSE corporate announcements | BSE India API | Yes | Board meetings, dividends, splits |
| BSE bulk / block deals | BSE India API | Yes | Large institutional trades |
| FII / DII activity | NSE daily CSV | Yes | Foreign vs domestic institutional flow |
| Social sentiment | Reddit PRAW | Yes | r/IndiaInvestments + r/IndianStockMarket |
| Insider transactions | yfinance `.NS` | Yes | |

---

## Files

### New files

| File | Purpose |
|------|---------|
| `tradingagents/dataflows/india_news.py` | ET Markets RSS + Google News RSS fetcher |
| `tradingagents/dataflows/india_bse.py` | BSE announcements + bulk/block deals |
| `tradingagents/dataflows/india_fii_dii.py` | NSE FII/DII daily flow fetcher |
| `tradingagents/dataflows/india_reddit.py` | Reddit sentiment via PRAW |
| `tradingagents/dataflows/india_report.py` | Kodryx-branded HTML report generator |
| `run_india.py` | Entry point: `python run_india.py --ticker TCS` |
| `.env` | All API keys and config |

### Modified files

| File | Change |
|------|--------|
| `tradingagents/dataflows/interface.py` | Add `india` vendor to `VENDOR_METHODS` for `get_news`, `get_global_news`, `get_insider_transactions` |
| `tradingagents/dataflows/__init__.py` | Export new modules |

### Untouched

All agent files, graph files, LLM clients, CLI — no changes.

---

## Module Details

### `india_news.py`
- Fetches ET Markets RSS: `https://economictimes.indiatimes.com/markets/rss.cms`
- Fetches Google News RSS per ticker: `https://news.google.com/rss/search?q=TCS+NSE+India&hl=en-IN`
- Fetches Google News RSS for India macro: queries for `RBI interest rate`, `Nifty Sensex`, `India inflation`, `rupee dollar`
- Deduplicates articles by title
- Returns formatted string matching existing `get_news_yfinance` output format

### `india_bse.py`
- **Announcements**: `https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?strCat=-1&strPrevDate=&strScrip={scrip_code}&strSearch=P&strToDate=&strType=C`
- **Bulk deals**: `https://api.bseindia.com/BseIndiaAPI/api/BulkDealData/w`
- Requires `Accept` + `Referer` headers to avoid 403
- Returns last 30 days of announcements, last 10 bulk deals
- Graceful fallback if scrip code not found

### `india_fii_dii.py`
- NSE publishes FII/DII data daily as CSV: `https://archives.nseindia.com/content/nsccl/fao_participant_vol.csv`
- Parses FII net buy/sell + DII net buy/sell for the latest available date
- Returns a formatted summary:
  ```
  FII Net Activity: -₹2,450 Cr (SELLING)
  DII Net Activity: +₹1,820 Cr (BUYING)
  Market Implication: Mixed — domestic support offsetting foreign outflow
  ```

### `india_reddit.py`
- Uses PRAW (Python Reddit API Wrapper)
- Searches `r/IndiaInvestments` + `r/IndianStockMarket` for posts mentioning the ticker
- Fetches top 20 posts from last 7 days, top 3 comments per post
- Credentials from `.env`: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`
- Returns sentiment summary: bullish/bearish post count + notable quotes

### `india_report.py`
- Takes the full agent state dict after graph completion
- Extracts: signal, confidence, CMP, P/E, 52W high/low, each agent's report, FII/DII data, BSE announcements
- Renders self-contained HTML using Kodryx design tokens (inline CSS, Google Fonts CDN)
- Saves to `reports/{ticker}_{YYYYMMDD}_{HHMMSS}.html`

---

## HTML Report Structure

```
Header
  Kodryx logo (top-left)
  "India Trading Agent" eyebrow (top-right)

Hero
  Eyebrow: "TCS.NS · NSE · {date}"
  H1: "Tata Consultancy Services"
  Signal badge: BUY / HOLD / SELL  (navy bg, gold text)
  Confidence: "72% Confidence"

  ⚠ Earnings alert banner (if results due within 14 days)

Metrics bar (4 cards, gold numbers)
  Current Market Price | P/E Ratio | 52-Week High | 52-Week Low

FII / DII Flow bar (2 cards)
  FII Net Flow (red if selling, green if buying)
  DII Net Flow

Analysis cards (one per agent)
  Fundamental Analysis
  Technical Analysis
  News & Sentiment        ← ET Markets + Google News
  Social Sentiment        ← Reddit r/IndiaInvestments + r/IndianStockMarket
  BSE Announcements       ← corporate filings
  BSE Bulk / Block Deals  ← institutional trades
  Bull Researcher
  Bear Researcher
  Risk Assessment

Final Recommendation (featured card, gold top-rule)
  Full reasoning from portfolio manager
  Signal: BUY / HOLD / SELL
```

Kodryx design tokens:
- Colors: `#0E2A3A` navy, `#C9A24D` gold, `#FFFFFF` white, `#6B7280` grey
- Fonts: Poppins (headings/metrics), Inter (body) — Google Fonts CDN
- Cards: `1px solid #EEF0F3` border, `8px` radius, no shadow, gold top-rule on featured card
- Metrics: Poppins 700, `#C9A24D` gold
- Eyebrows: Inter 600, uppercase, `letter-spacing: 0.08em`
- Signal badge: navy background, gold text, pill shape

---

## Entry Point

```bash
python run_india.py --ticker TCS --date 2026-04-29
```

Output:
- Terminal: agent progress
- File: `reports/TCS_20260429_HHMMSS.html`

---

## Environment Variables (.env)

```env
# LLM
OPENROUTER_API_KEY=eyJhbGci...  # clod.io key goes here

# Reddit (PRAW)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=IndiaStockAgent/1.0

# Optional overrides
TRADINGAGENTS_RESULTS_DIR=./reports
```

---

## BSE Scrip Code Map

Hardcoded dict in `india_bse.py` — extendable:

```python
BSE_SCRIP_CODES = {
    "TCS":       "532540",
    "RELIANCE":  "500325",
    "INFY":      "500209",
    "HDFCBANK":  "500180",
    "WIPRO":     "507685",
    "ICICIBANK": "532174",
    "BAJFINANCE":"500034",
    "TATAMOTORS":"500570",
    "ADANIENT":  "512599",
    "HINDUNILVR":"500696",
}
```

If scrip code not found, BSE section shows "Scrip code not configured — add to BSE_SCRIP_CODES" gracefully.

---

## Constraints

- Research only — no live trading, no order placement
- No paid APIs — 100% free data sources
- Report is static HTML — no server, no database
- All credentials in `.env`, never hardcoded
- Reddit credentials required for social sentiment; agent runs without them (section shows "Reddit credentials not configured")
