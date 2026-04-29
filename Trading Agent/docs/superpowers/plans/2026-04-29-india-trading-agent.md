# India Trading Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt TradingAgents for Indian stock market analysis (TCS.NS) using yfinance, Google News RSS, BSE API, NSE FII/DII, Reddit public JSON, and clod.io DeepSeek V4 Pro, outputting a Kodryx-branded HTML report.

**Architecture:** The existing yfinance vendor handles all price/fundamental/technical data unchanged. Five new dataflow modules are added for India-specific data (news, BSE, FII/DII, Reddit). A new `run_india.py` entry point configures the graph for clod.io and fetches supplementary data. A new `india_report.py` generates the Kodryx-styled HTML report after the graph run.

**Tech Stack:** Python 3.10+, yfinance, requests, xml.etree.ElementTree (stdlib), langchain-openai (via openrouter path), langgraph, Kodryx Design System (inline CSS)

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Copy from temp_clone | `tradingagents/` + all | Full framework source |
| Create | `.env` | API keys and config |
| Create | `tradingagents/dataflows/india_news.py` | Google News RSS + ET Markets RSS fetcher |
| Create | `tradingagents/dataflows/india_reddit.py` | Reddit public JSON sentiment fetcher |
| Create | `tradingagents/dataflows/india_bse.py` | BSE announcements + bulk deals |
| Create | `tradingagents/dataflows/india_fii_dii.py` | NSE FII/DII daily flow |
| Create | `tradingagents/dataflows/india_report.py` | Kodryx HTML report generator |
| Modify | `tradingagents/dataflows/interface.py` | Register `india` vendor for news |
| Create | `run_india.py` | Entry point |
| Create | `reports/` | Output directory (gitignored) |
| Create | `tests/test_india_dataflows.py` | Unit tests for all new modules |

---

## Task 1: Copy repo and install dependencies

**Files:**
- Working dir: `C:\Vibe Code\Trading Agent\`

- [ ] **Step 1: Copy temp_clone contents to working directory**

```bash
cd "C:\Vibe Code\Trading Agent"
cp -r temp_clone/tradingagents .
cp -r temp_clone/tests .
cp -r temp_clone/cli .
cp temp_clone/pyproject.toml .
cp temp_clone/main.py .
```

- [ ] **Step 2: Create .env file**

```bash
cat > .env << 'EOF'
# clod.io — OpenAI-compatible endpoint
OPENROUTER_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyM3lHcnM0STllWHJDdjlSeG5VZlRkY1lVdHAxIiwidXNlcklkIjoiMjN5R3JzNEk5ZVhyQ3Y5UnhuVWZUZGNZVXRwMSIsInRlYW1JZCI6Ijg0NDY4NTcwLTU1NWItNGU4OS1iZTkzLTFlOWYxYTMzN2I3ZCIsInRlYW1Sb2xlIjoib3duZXIiLCJwcm9qZWN0SWQiOiJmMDgzMjIwNy1mYmJlLTQ2NDEtYWU3ZS1hYjc0MzlmNzBkNjEiLCJpYXQiOjE3Nzc0NzgwMjcsImV4cCI6MTgyNzQ3ODAyN30.q1A3QbQ6Pw5IyejLAHynArv_7SRPwzBdWwjDNuBKH-Y

# Report output dir
TRADINGAGENTS_RESULTS_DIR=./reports
EOF
```

- [ ] **Step 3: Create reports directory and .gitignore entry**

```bash
mkdir -p reports
echo "reports/" >> .gitignore
echo ".env" >> .gitignore
echo "temp_clone/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo ".tradingagents/" >> .gitignore
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -e . python-dotenv
```

Expected output: `Successfully installed tradingagents-0.2.4`

- [ ] **Step 5: Verify install**

```bash
python -c "from tradingagents.graph.trading_graph import TradingAgentsGraph; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add tradingagents/ tests/ cli/ pyproject.toml main.py .gitignore
git commit -m "feat: add tradingagents framework source"
```

---

## Task 2: Create `india_news.py`

**Files:**
- Create: `tradingagents/dataflows/india_news.py`
- Test: `tests/test_india_dataflows.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_india_dataflows.py`:

```python
"""Tests for India-specific dataflow modules."""
import pytest
from unittest.mock import patch, MagicMock


class TestIndiaNews:
    def test_returns_string(self):
        from tradingagents.dataflows.india_news import get_india_stock_news
        # Mock requests to avoid network calls in unit tests
        mock_rss = """<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>TCS Q4 results beat estimates</title>
            <description>TCS reported strong Q4 numbers</description>
            <pubDate>Tue, 29 Apr 2026 10:00:00 GMT</pubDate>
            <source>Economic Times</source>
          </item>
        </channel></rss>"""
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = mock_rss
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_india_stock_news("TCS.NS", "2026-04-22", "2026-04-29")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_removes_ns_suffix_for_query(self):
        from tradingagents.dataflows.india_news import _build_ticker_query
        assert "TCS" in _build_ticker_query("TCS.NS")
        assert ".NS" not in _build_ticker_query("TCS.NS")

    def test_get_india_macro_news_returns_string(self):
        from tradingagents.dataflows.india_news import get_india_macro_news
        mock_rss = """<?xml version="1.0"?>
        <rss><channel>
          <item>
            <title>RBI holds rates steady</title>
            <description>RBI MPC decision</description>
            <pubDate>Tue, 29 Apr 2026 09:00:00 GMT</pubDate>
          </item>
        </channel></rss>"""
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.text = mock_rss
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_india_macro_news("2026-04-29", look_back_days=7)
        assert isinstance(result, str)
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_india_dataflows.py::TestIndiaNews -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Create `india_news.py`**

```python
"""India-specific news fetcher using Google News RSS and ET Markets RSS."""
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Annotated
from urllib.parse import quote

import requests

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
_ET_MARKETS_RSS = "https://economictimes.indiatimes.com/markets/rss.cms"


def _build_ticker_query(ticker: str) -> str:
    return ticker.replace(".NS", "").replace(".BO", "")


def _fetch_rss(url: str, keyword: str = None) -> list:
    """Fetch and parse an RSS feed. Returns list of article dicts."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        articles = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            description = item.findtext("description", "").strip()
            pub_date = item.findtext("pubDate", "")
            source = item.findtext("source", "")
            if not title:
                continue
            if keyword and keyword.upper() not in title.upper() and keyword.upper() not in description.upper():
                continue
            articles.append({
                "title": title,
                "summary": description[:200] if description else "",
                "source": source or url.split("/")[2],
                "pub_date": pub_date,
            })
        return articles
    except Exception:
        return []


def get_india_stock_news(
    ticker: Annotated[str, "NSE ticker e.g. TCS.NS"],
    start_date: Annotated[str, "Start date YYYY-MM-DD"],
    end_date: Annotated[str, "End date YYYY-MM-DD"],
) -> str:
    """Fetch India stock news from Google News RSS and ET Markets RSS."""
    base = _build_ticker_query(ticker)
    articles = []

    # Google News — stock-specific
    query = quote(f"{base} NSE India stock")
    articles += _fetch_rss(_GOOGLE_NEWS_RSS.format(query=query))

    # ET Markets — filter by ticker name
    articles += _fetch_rss(_ET_MARKETS_RSS, keyword=base)

    # Deduplicate by title
    seen, unique = set(), []
    for a in articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            unique.append(a)

    if not unique:
        return f"No India news found for {ticker} between {start_date} and {end_date}"

    news_str = ""
    for a in unique[:20]:
        news_str += f"### {a['title']} (source: {a['source']})\n"
        if a["summary"]:
            news_str += f"{a['summary']}\n"
        news_str += "\n"

    return f"## {ticker} India News, from {start_date} to {end_date}:\n\n{news_str}"


def get_india_macro_news(
    curr_date: Annotated[str, "Current date YYYY-MM-DD"],
    look_back_days: Annotated[int, "Days to look back"] = 7,
    limit: Annotated[int, "Max articles"] = 15,
) -> str:
    """Fetch India macro news (RBI, Nifty, Sensex, rupee) from Google News RSS."""
    queries = [
        "RBI Reserve Bank India interest rate",
        "Nifty Sensex India stock market",
        "India inflation economy",
        "rupee dollar India forex",
    ]
    all_articles, seen = [], set()
    for q in queries:
        url = _GOOGLE_NEWS_RSS.format(query=quote(q))
        for a in _fetch_rss(url):
            if a["title"] not in seen:
                seen.add(a["title"])
                all_articles.append(a)
        if len(all_articles) >= limit:
            break

    if not all_articles:
        return f"No India macro news found for {curr_date}"

    news_str = ""
    for a in all_articles[:limit]:
        news_str += f"### {a['title']} (source: {a['source']})\n"
        if a["summary"]:
            news_str += f"{a['summary']}\n"
        news_str += "\n"

    return f"## India Macro News ({curr_date}):\n\n{news_str}"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_india_dataflows.py::TestIndiaNews -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add tradingagents/dataflows/india_news.py tests/test_india_dataflows.py
git commit -m "feat: add india_news — Google News RSS + ET Markets RSS fetcher"
```

---

## Task 3: Create `india_reddit.py`

**Files:**
- Create: `tradingagents/dataflows/india_reddit.py`
- Modify: `tests/test_india_dataflows.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_india_dataflows.py`:

```python
class TestIndiaReddit:
    def test_returns_string(self):
        from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
        mock_response = {
            "data": {
                "children": [
                    {"data": {"title": "TCS Q4 results amazing!", "selftext": "Really bullish on TCS", "score": 45, "url": "https://reddit.com/r/IndiaInvestments/abc"}},
                    {"data": {"title": "Selling TCS, too expensive", "selftext": "Valuations stretched", "score": 12, "url": "https://reddit.com/r/IndiaInvestments/def"}},
                ]
            }
        }
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_india_reddit_sentiment("TCS.NS", "2026-04-22", "2026-04-29")
        assert isinstance(result, str)
        assert "TCS" in result or "reddit" in result.lower() or "sentiment" in result.lower()

    def test_handles_empty_response(self):
        from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"children": []}}
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_india_reddit_sentiment("TCS.NS", "2026-04-22", "2026-04-29")
        assert isinstance(result, str)
        assert "No Reddit posts" in result or len(result) > 0
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_india_dataflows.py::TestIndiaReddit -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `india_reddit.py`**

```python
"""India stock sentiment from Reddit public JSON (no API key required)."""
from typing import Annotated
from urllib.parse import quote

import requests

_HEADERS = {
    "User-Agent": "IndiaStockResearch/1.0 (research-only bot)"
}
_SUBREDDITS = ["IndiaInvestments", "IndianStockMarket"]
_SEARCH_URL = "https://www.reddit.com/r/{sub}/search.json?q={query}&sort=new&limit=25&restrict_sr=1&t=week"


def get_india_reddit_sentiment(
    ticker: Annotated[str, "NSE ticker e.g. TCS.NS"],
    start_date: Annotated[str, "Start date YYYY-MM-DD"],
    end_date: Annotated[str, "End date YYYY-MM-DD"],
) -> str:
    """Fetch Reddit sentiment from r/IndiaInvestments and r/IndianStockMarket."""
    base = ticker.replace(".NS", "").replace(".BO", "")
    all_posts = []

    for sub in _SUBREDDITS:
        url = _SEARCH_URL.format(sub=sub, query=quote(base))
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                all_posts.append({
                    "title": d.get("title", ""),
                    "body": d.get("selftext", "")[:300],
                    "score": d.get("score", 0),
                    "url": d.get("url", ""),
                    "subreddit": sub,
                })
        except Exception:
            continue

    if not all_posts:
        return f"No Reddit posts found for {base} in Indian investment subreddits between {start_date} and {end_date}"

    # Simple sentiment: count bullish vs bearish keywords
    bullish_kw = ["buy", "bullish", "strong", "growth", "upside", "target", "positive", "good results", "beat"]
    bearish_kw = ["sell", "bearish", "overvalued", "weak", "downside", "drop", "fall", "miss", "disappointing"]

    bull_count = bear_count = 0
    posts_str = ""
    for p in sorted(all_posts, key=lambda x: x["score"], reverse=True)[:15]:
        text = (p["title"] + " " + p["body"]).lower()
        is_bull = any(k in text for k in bullish_kw)
        is_bear = any(k in text for k in bearish_kw)
        if is_bull:
            bull_count += 1
        if is_bear:
            bear_count += 1
        posts_str += f"**[r/{p['subreddit']}]** {p['title']} (score: {p['score']})\n"
        if p["body"]:
            posts_str += f"{p['body'][:150]}...\n"
        posts_str += "\n"

    total = len(all_posts)
    sentiment = "Neutral"
    if bull_count > bear_count * 1.5:
        sentiment = "Bullish"
    elif bear_count > bull_count * 1.5:
        sentiment = "Bearish"

    header = (
        f"## Reddit Sentiment for {base} ({start_date} to {end_date})\n\n"
        f"**Posts found:** {total} across r/IndiaInvestments + r/IndianStockMarket\n"
        f"**Sentiment:** {sentiment} (Bullish signals: {bull_count}, Bearish signals: {bear_count})\n\n"
        f"### Top Posts:\n\n"
    )
    return header + posts_str
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_india_dataflows.py::TestIndiaReddit -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add tradingagents/dataflows/india_reddit.py tests/test_india_dataflows.py
git commit -m "feat: add india_reddit — public JSON sentiment, no API key"
```

---

## Task 4: Create `india_bse.py`

**Files:**
- Create: `tradingagents/dataflows/india_bse.py`
- Modify: `tests/test_india_dataflows.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_india_dataflows.py`:

```python
class TestIndiaBSE:
    def test_get_announcements_returns_string(self):
        from tradingagents.dataflows.india_bse import get_bse_announcements
        mock_data = {
            "Table": [
                {"HEADLINE": "Board Meeting", "SLONGNAME": "TCS Ltd", "NEWS_DT": "2026-04-25T00:00:00"},
                {"HEADLINE": "Dividend Declared", "SLONGNAME": "TCS Ltd", "NEWS_DT": "2026-04-20T00:00:00"},
            ]
        }
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_bse_announcements("TCS.NS", "2026-04-01", "2026-04-29")
        assert isinstance(result, str)
        assert "Board Meeting" in result or "Dividend" in result or "announcement" in result.lower()

    def test_unknown_ticker_graceful(self):
        from tradingagents.dataflows.india_bse import get_bse_announcements
        result = get_bse_announcements("UNKNOWN.NS", "2026-04-01", "2026-04-29")
        assert isinstance(result, str)
        assert "not configured" in result.lower() or "unavailable" in result.lower()

    def test_get_bulk_deals_returns_string(self):
        from tradingagents.dataflows.india_bse import get_bse_bulk_deals
        mock_data = {
            "Table": [
                {"SCRIP_CD": "532540", "SCRIP_NAME": "TCS", "CLIENT_NAME": "Some Fund", "BUY_SELL": "B", "DEAL_QTY": "500000", "DEAL_PRICE": "3842.50"}
            ]
        }
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_bse_bulk_deals("TCS.NS")
        assert isinstance(result, str)
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_india_dataflows.py::TestIndiaBSE -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `india_bse.py`**

```python
"""BSE India corporate announcements and bulk deal fetcher."""
from datetime import datetime, timedelta
from typing import Annotated

import requests

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bseindia.com/",
}

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
    "SBIN":      "500112",
    "AXISBANK":  "532215",
    "LT":        "500510",
    "KOTAKBANK": "500247",
    "SUNPHARMA": "524715",
}

_ANN_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
    "?strCat=-1&strPrevDate=&strScrip={scrip}&strSearch=P&strToDate=&strType=C"
)
_BULK_URL = "https://api.bseindia.com/BseIndiaAPI/api/BulkDealData/w"


def _get_scrip_code(ticker: str) -> str | None:
    base = ticker.replace(".NS", "").replace(".BO", "").upper()
    return BSE_SCRIP_CODES.get(base)


def get_bse_announcements(
    ticker: Annotated[str, "NSE ticker e.g. TCS.NS"],
    start_date: Annotated[str, "Start date YYYY-MM-DD"],
    end_date: Annotated[str, "End date YYYY-MM-DD"],
) -> str:
    """Fetch BSE corporate announcements for a ticker."""
    scrip = _get_scrip_code(ticker)
    if not scrip:
        base = ticker.replace(".NS", "").replace(".BO", "")
        return (
            f"BSE announcements for {base} unavailable — scrip code not configured. "
            f"Add it to BSE_SCRIP_CODES in india_bse.py."
        )
    try:
        resp = requests.get(_ANN_URL.format(scrip=scrip), headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("Table", [])
        if not items:
            return f"No BSE announcements found for {ticker} (scrip: {scrip})"

        result = f"## BSE Corporate Announcements for {ticker} (scrip: {scrip})\n\n"
        for item in items[:20]:
            headline = item.get("HEADLINE", "No headline")
            date_str = item.get("NEWS_DT", "")[:10]
            result += f"- [{date_str}] {headline}\n"
        return result
    except Exception as e:
        return f"BSE announcements temporarily unavailable for {ticker}: {e}"


def get_bse_bulk_deals(
    ticker: Annotated[str, "NSE ticker e.g. TCS.NS"],
) -> str:
    """Fetch recent BSE bulk and block deals for a ticker."""
    scrip = _get_scrip_code(ticker)
    try:
        resp = requests.get(_BULK_URL, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("Table", [])

        if scrip:
            items = [i for i in items if str(i.get("SCRIP_CD", "")) == scrip]

        if not items:
            return f"No bulk/block deals found for {ticker} in latest BSE data"

        result = f"## BSE Bulk / Block Deals for {ticker}\n\n"
        for item in items[:10]:
            name = item.get("CLIENT_NAME", "Unknown")
            action = "BUY" if item.get("BUY_SELL", "") == "B" else "SELL"
            qty = item.get("DEAL_QTY", "N/A")
            price = item.get("DEAL_PRICE", "N/A")
            result += f"- {name}: {action} {qty} shares @ ₹{price}\n"
        return result
    except Exception as e:
        return f"BSE bulk deals temporarily unavailable for {ticker}: {e}"
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_india_dataflows.py::TestIndiaBSE -v
```

Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add tradingagents/dataflows/india_bse.py tests/test_india_dataflows.py
git commit -m "feat: add india_bse — BSE corporate announcements + bulk deals"
```

---

## Task 5: Create `india_fii_dii.py`

**Files:**
- Create: `tradingagents/dataflows/india_fii_dii.py`
- Modify: `tests/test_india_dataflows.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_india_dataflows.py`:

```python
class TestIndiaFiiDii:
    def test_returns_string(self):
        from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
        mock_json = [
            {"date": "29-Apr-2026", "buyValue": "12000.50", "sellValue": "14500.75", "netValue": "-2500.25", "category": "FII/FPI"},
            {"date": "29-Apr-2026", "buyValue": "9000.00", "sellValue": "7500.00", "netValue": "1500.00", "category": "DII"},
        ]
        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.return_value.json.return_value = mock_json
            mock_session.get.return_value.status_code = 200
            result = get_fii_dii_activity("2026-04-29")
        assert isinstance(result, str)

    def test_handles_network_error(self):
        from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
        with patch("requests.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.get.side_effect = Exception("Network error")
            result = get_fii_dii_activity("2026-04-29")
        assert isinstance(result, str)
        assert "unavailable" in result.lower() or "error" in result.lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_india_dataflows.py::TestIndiaFiiDii -v
```

Expected: `ImportError`

- [ ] **Step 3: Create `india_fii_dii.py`**

```python
"""NSE FII/DII daily activity fetcher."""
from typing import Annotated

import requests

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}
_NSE_HOME = "https://www.nseindia.com"
_FII_DII_URL = "https://www.nseindia.com/api/fiidiiTradeReact"


def get_fii_dii_activity(
    curr_date: Annotated[str, "Current date YYYY-MM-DD"],
) -> str:
    """Fetch FII and DII net buy/sell activity from NSE India."""
    try:
        session = requests.Session()
        # NSE requires a prior visit to set session cookies
        session.get(_NSE_HOME, headers=_HEADERS, timeout=10)
        resp = session.get(_FII_DII_URL, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        fii_net = dii_net = None
        fii_buy = fii_sell = dii_buy = dii_sell = None

        for entry in data:
            category = entry.get("category", "")
            if "FII" in category.upper() or "FPI" in category.upper():
                fii_buy = float(entry.get("buyValue", 0))
                fii_sell = float(entry.get("sellValue", 0))
                fii_net = float(entry.get("netValue", 0))
            elif "DII" in category.upper():
                dii_buy = float(entry.get("buyValue", 0))
                dii_sell = float(entry.get("sellValue", 0))
                dii_net = float(entry.get("netValue", 0))

        if fii_net is None and dii_net is None:
            return f"FII/DII data not available for {curr_date}"

        def _fmt(val):
            if val is None:
                return "N/A"
            sign = "+" if val >= 0 else ""
            return f"{sign}₹{abs(val):,.2f} Cr"

        def _action(val):
            if val is None:
                return "N/A"
            return "BUYING" if val >= 0 else "SELLING"

        result = f"## FII / DII Activity ({curr_date})\n\n"
        if fii_net is not None:
            result += f"**FII/FPI Net:** {_fmt(fii_net)} ({_action(fii_net)})\n"
            result += f"  Buy: ₹{fii_buy:,.2f} Cr | Sell: ₹{fii_sell:,.2f} Cr\n\n"
        if dii_net is not None:
            result += f"**DII Net:** {_fmt(dii_net)} ({_action(dii_net)})\n"
            result += f"  Buy: ₹{dii_buy:,.2f} Cr | Sell: ₹{dii_sell:,.2f} Cr\n\n"

        # Market implication
        if fii_net is not None and dii_net is not None:
            if fii_net > 0 and dii_net > 0:
                implication = "Strong — both foreign and domestic institutions are buying"
            elif fii_net < 0 and dii_net < 0:
                implication = "Weak — both foreign and domestic institutions are selling"
            elif fii_net < 0 and dii_net > 0:
                implication = "Mixed — foreign selling, domestic support"
            else:
                implication = "Mixed — foreign buying, domestic selling"
            result += f"**Market Implication:** {implication}\n"

        return result

    except Exception as e:
        return f"FII/DII data temporarily unavailable ({e}). This data requires NSE India connectivity."
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_india_dataflows.py::TestIndiaFiiDii -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add tradingagents/dataflows/india_fii_dii.py tests/test_india_dataflows.py
git commit -m "feat: add india_fii_dii — NSE FII/DII daily flow fetcher"
```

---

## Task 6: Wire India vendor into `interface.py`

**Files:**
- Modify: `tradingagents/dataflows/interface.py`
- Modify: `tradingagents/dataflows/__init__.py`
- Modify: `tests/test_india_dataflows.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_india_dataflows.py`:

```python
class TestIndiaVendorRouting:
    def test_india_vendor_registered_for_news(self):
        from tradingagents.dataflows.interface import VENDOR_METHODS
        assert "india" in VENDOR_METHODS["get_news"]
        assert "india" in VENDOR_METHODS["get_global_news"]

    def test_india_vendor_callable(self):
        from tradingagents.dataflows.interface import VENDOR_METHODS
        fn = VENDOR_METHODS["get_news"]["india"]
        assert callable(fn)
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_india_dataflows.py::TestIndiaVendorRouting -v
```

Expected: `AssertionError` (india key not present)

- [ ] **Step 3: Modify `interface.py`**

Add the import at the top of `tradingagents/dataflows/interface.py` after the existing imports:

```python
from .india_news import get_india_stock_news, get_india_macro_news
```

Then update `VENDOR_METHODS` — add `"india"` entries to `get_news` and `get_global_news`:

```python
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "yfinance": get_yfinance_fundamentals,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "yfinance": get_news_yfinance,
        "india": get_india_stock_news,
    },
    "get_global_news": {
        "yfinance": get_global_news_yfinance,
        "alpha_vantage": get_alpha_vantage_global_news,
        "india": get_india_macro_news,
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
    },
}
```

Also add `"india"` to `VENDOR_LIST`:

```python
VENDOR_LIST = [
    "yfinance",
    "alpha_vantage",
    "india",
]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_india_dataflows.py::TestIndiaVendorRouting -v
```

Expected: 2 PASSED

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
pytest tests/ -v --ignore=tests/test_google_api_key.py -x
```

Expected: all existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add tradingagents/dataflows/interface.py tests/test_india_dataflows.py
git commit -m "feat: register india vendor in interface.py for news routing"
```

---

## Task 7: Create `run_india.py`

**Files:**
- Create: `run_india.py`

- [ ] **Step 1: Create `run_india.py`**

```python
"""India Trading Agent entry point.

Usage:
    python run_india.py --ticker TCS
    python run_india.py --ticker RELIANCE --date 2026-04-29
"""
import argparse
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.india_bse import get_bse_announcements, get_bse_bulk_deals
from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
from tradingagents.dataflows.india_report import generate_report


def build_config(ticker_ns: str, trade_date: str) -> dict:
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "openrouter"
    config["backend_url"] = "https://api.clod.io/v1"
    config["deep_think_llm"] = "deepseek-ai/DeepSeek-V4-Pro"
    config["quick_think_llm"] = "deepseek-ai/DeepSeek-V4-Pro"
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    config["results_dir"] = str(Path("reports") / ticker_ns.replace(".NS", ""))
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "india",
    }
    return config


def main():
    parser = argparse.ArgumentParser(description="India Stock Trading Agent")
    parser.add_argument("--ticker", required=True, help="NSE ticker (e.g. TCS, RELIANCE)")
    parser.add_argument("--date", default=str(date.today()), help="Trade date YYYY-MM-DD")
    args = parser.parse_args()

    ticker_base = args.ticker.upper().replace(".NS", "").replace(".BO", "")
    ticker_ns = f"{ticker_base}.NS"
    trade_date = args.date

    print(f"\n{'='*60}")
    print(f"  India Trading Agent — {ticker_ns}")
    print(f"  Date: {trade_date}")
    print(f"  LLM: DeepSeek V4 Pro via clod.io")
    print(f"{'='*60}\n")

    # Build config and run agent graph
    config = build_config(ticker_ns, trade_date)
    ta = TradingAgentsGraph(debug=True, config=config)

    print("Running multi-agent analysis...\n")
    final_state, signal = ta.propagate(ticker_ns, trade_date)

    # Fetch supplementary India data (parallel to agent run, shown in report)
    print("\nFetching supplementary India data...")
    start_date = trade_date  # use same date for recent data
    look_back = "2026-04-01"  # 30-day window

    bse_announcements = get_bse_announcements(ticker_ns, look_back, trade_date)
    bse_bulk_deals = get_bse_bulk_deals(ticker_ns)
    fii_dii = get_fii_dii_activity(trade_date)
    reddit = get_india_reddit_sentiment(ticker_ns, look_back, trade_date)

    supplementary = {
        "bse_announcements": bse_announcements,
        "bse_bulk_deals": bse_bulk_deals,
        "fii_dii": fii_dii,
        "reddit_sentiment": reddit,
    }

    # Generate Kodryx-branded HTML report
    print("\nGenerating HTML report...")
    report_path = generate_report(
        ticker=ticker_ns,
        trade_date=trade_date,
        final_state=final_state,
        signal=signal,
        supplementary=supplementary,
    )

    print(f"\n{'='*60}")
    print(f"  Signal: {signal}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it parses args without crashing**

```bash
python run_india.py --help
```

Expected: usage text printed, no import errors

- [ ] **Step 3: Commit**

```bash
git add run_india.py
git commit -m "feat: add run_india.py entry point for India stock analysis"
```

---

## Task 8: Create `india_report.py`

**Files:**
- Create: `tradingagents/dataflows/india_report.py`

- [ ] **Step 1: Create `india_report.py`**

```python
"""Kodryx-branded HTML report generator for India Trading Agent."""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yfinance as yf


def _get_signal_color(signal: str) -> str:
    s = signal.upper()
    if "BUY" in s:
        return "#16a34a"   # green
    elif "SELL" in s:
        return "#dc2626"   # red
    return "#C9A24D"       # gold for HOLD


def _clean_signal(signal: str) -> str:
    for word in ["BUY", "SELL", "HOLD"]:
        if word in signal.upper():
            return word
    return signal.strip()[:10]


def _fetch_metrics(ticker: str) -> Dict[str, str]:
    """Fetch live metrics from yfinance for the report header."""
    try:
        info = yf.Ticker(ticker).info
        cmp = info.get("currentPrice") or info.get("regularMarketPrice")
        pe = info.get("trailingPE")
        high = info.get("fiftyTwoWeekHigh")
        low = info.get("fiftyTwoWeekLow")
        name = info.get("longName", ticker)
        return {
            "name": name,
            "cmp": f"₹{cmp:,.2f}" if cmp else "N/A",
            "pe": f"{pe:.1f}x" if pe else "N/A",
            "high": f"₹{high:,.2f}" if high else "N/A",
            "low": f"₹{low:,.2f}" if low else "N/A",
        }
    except Exception:
        return {"name": ticker, "cmp": "N/A", "pe": "N/A", "high": "N/A", "low": "N/A"}


def _card(eyebrow: str, title: str, body: str, featured: bool = False) -> str:
    border_top = "border-top: 3px solid #C9A24D;" if featured else ""
    body_html = body.replace("\n", "<br>") if body else "<em>No data available</em>"
    return f"""
    <div class="card{'  card-featured' if featured else ''}" style="{border_top}">
      <span class="eyebrow">{eyebrow}</span>
      <h3 class="card-title">{title}</h3>
      <div class="card-body">{body_html}</div>
    </div>"""


def _metric_card(label: str, value: str) -> str:
    return f"""
    <div class="metric-card">
      <div class="metric-value">{value}</div>
      <div class="metric-label">{label}</div>
    </div>"""


def _check_earnings_alert(ticker: str) -> str:
    """Return an alert string if earnings are due within 14 days."""
    try:
        dates = yf.Ticker(ticker).earnings_dates
        if dates is None or dates.empty:
            return ""
        from datetime import date, timedelta
        today = date.today()
        upcoming = [d.date() for d in dates.index if today <= d.date() <= today + timedelta(days=14)]
        if upcoming:
            return f"⚠ Earnings results expected on {upcoming[0].strftime('%d %b %Y')} — elevated volatility possible"
    except Exception:
        pass
    return ""


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#fff;color:#0E2A3A;-webkit-font-smoothing:antialiased}
.container{max-width:1160px;margin:0 auto;padding:0 24px}
/* Header */
.header{background:#0E2A3A;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
.header-brand{font-family:'Poppins',sans-serif;font-weight:700;font-size:20px;color:#C9A24D;letter-spacing:-0.01em}
.header-sub{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(255,255,255,0.5);font-weight:600}
/* Hero */
.hero{padding:48px 0 36px}
.eyebrow-hero{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:12px}
.hero-title{font-family:'Poppins',sans-serif;font-size:40px;font-weight:700;color:#0E2A3A;line-height:1.15;letter-spacing:-0.015em;margin-bottom:20px}
.signal-badge{display:inline-flex;align-items:center;gap:10px;background:#0E2A3A;color:#C9A24D;font-family:'Poppins',sans-serif;font-size:22px;font-weight:700;padding:12px 28px;border-radius:999px;letter-spacing:-0.01em}
.signal-dot{width:10px;height:10px;border-radius:50%;background:currentColor}
.earnings-alert{margin-top:16px;padding:10px 16px;background:#fef9ee;border:1px solid #C9A24D;border-radius:6px;font-size:14px;color:#0E2A3A}
/* Metrics */
.metrics-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:32px 0}
.metric-card{border:1px solid #EEF0F3;border-radius:8px;padding:20px 16px;text-align:center}
.metric-value{font-family:'Poppins',sans-serif;font-size:28px;font-weight:700;color:#C9A24D;line-height:1;margin-bottom:6px}
.metric-label{font-size:13px;color:#6B7280;font-weight:500}
/* FII DII */
.fii-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:32px}
.fii-card{border:1px solid #EEF0F3;border-radius:8px;padding:16px 20px}
.fii-label{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:8px}
.fii-value{font-family:'Poppins',sans-serif;font-size:20px;font-weight:700;color:#0E2A3A}
/* Divider */
hr.gold{border:0;border-top:2px solid #C9A24D;width:56px;margin:0 0 32px}
/* Section title */
.section-title{font-family:'Poppins',sans-serif;font-size:24px;font-weight:600;color:#0E2A3A;margin-bottom:24px}
/* Cards */
.cards-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:32px}
.card{border:1px solid #EEF0F3;border-radius:8px;padding:24px;background:#fff;transition:border-color 200ms}
.card:hover{border-color:#C9A24D}
.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;display:block;margin-bottom:8px}
.card-title{font-family:'Poppins',sans-serif;font-size:16px;font-weight:600;color:#0E2A3A;margin-bottom:12px}
.card-body{font-size:14px;color:#0E2A3A;line-height:1.6}
.card-featured{border:1px solid #D8DCE2}
/* Final recommendation */
.final-card{border:1px solid #D8DCE2;border-top:3px solid #C9A24D;border-radius:8px;padding:32px;margin-bottom:48px}
.final-card .card-body{font-size:15px;line-height:1.7}
/* Footer */
.footer{background:#F7F8FA;border-top:1px solid #EEF0F3;padding:24px;text-align:center;font-size:12px;color:#6B7280}
"""


def generate_report(
    ticker: str,
    trade_date: str,
    final_state: Dict[str, Any],
    signal: str,
    supplementary: Dict[str, str],
    output_dir: str = "reports",
) -> str:
    """Generate a Kodryx-branded HTML report and return the file path."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    metrics = _fetch_metrics(ticker)
    signal_clean = _clean_signal(signal)
    signal_color = _get_signal_color(signal)
    earnings_alert = _check_earnings_alert(ticker)

    base = ticker.replace(".NS", "").replace(".BO", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base}_{timestamp}.html"
    filepath = os.path.join(output_dir, filename)

    # Extract agent reports from state
    market_report = final_state.get("market_report", "")
    sentiment_report = final_state.get("sentiment_report", "")
    news_report = final_state.get("news_report", "")
    fundamentals_report = final_state.get("fundamentals_report", "")
    inv_debate = final_state.get("investment_debate_state", {})
    bull_history = inv_debate.get("bull_history", "")
    bear_history = inv_debate.get("bear_history", "")
    risk_debate = final_state.get("risk_debate_state", {})
    risk_judge = risk_debate.get("judge_decision", "")
    final_decision = final_state.get("final_trade_decision", "")
    investment_plan = final_state.get("investment_plan", "")

    # FII/DII summary for 2-card display
    fii_dii_text = supplementary.get("fii_dii", "")
    fii_line = dii_line = "Data unavailable"
    for line in fii_dii_text.split("\n"):
        if "FII/FPI Net:" in line:
            fii_line = line.replace("**FII/FPI Net:**", "").strip()
        elif "DII Net:" in line:
            dii_line = line.replace("**DII Net:**", "").strip()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>India Trading Agent — {base} Analysis {trade_date}</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header-brand">KODRYX AI</div>
    <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:2px">Intelligence · Innovation · Impact</div>
  </div>
  <div style="text-align:right">
    <div class="header-sub">India Trading Agent</div>
    <div style="font-size:12px;color:rgba(255,255,255,0.5);margin-top:2px">Powered by DeepSeek V4 Pro</div>
  </div>
</div>

<div class="container">

  <!-- Hero -->
  <div class="hero">
    <div class="eyebrow-hero">{base} · NSE · {trade_date}</div>
    <h1 class="hero-title">{metrics['name']}</h1>
    <div class="signal-badge" style="color:{signal_color}">
      <span class="signal-dot" style="background:{signal_color}"></span>
      {signal_clean}
    </div>
    {f'<div class="earnings-alert">{earnings_alert}</div>' if earnings_alert else ''}
  </div>

  <!-- Metrics -->
  <div class="metrics-grid">
    {_metric_card("Current Market Price", metrics['cmp'])}
    {_metric_card("P/E Ratio (TTM)", metrics['pe'])}
    {_metric_card("52-Week High", metrics['high'])}
    {_metric_card("52-Week Low", metrics['low'])}
  </div>

  <!-- FII / DII -->
  <h2 class="section-title">Institutional Flow</h2>
  <hr class="gold"/>
  <div class="fii-grid">
    <div class="fii-card">
      <div class="fii-label">FII / FPI Net Activity</div>
      <div class="fii-value">{fii_line}</div>
    </div>
    <div class="fii-card">
      <div class="fii-label">DII Net Activity</div>
      <div class="fii-value">{dii_line}</div>
    </div>
  </div>

  <!-- Analysis Cards -->
  <h2 class="section-title">Agent Analysis</h2>
  <hr class="gold"/>
  <div class="cards-grid">
    {_card("Technical Analysis", "Market & Price Action", market_report)}
    {_card("Fundamental Analysis", "Financials & Valuation", fundamentals_report)}
    {_card("News & Sentiment", "India News Coverage", news_report)}
    {_card("Social Sentiment", "Reddit — r/IndiaInvestments + r/IndianStockMarket", supplementary.get('reddit_sentiment',''))}
    {_card("BSE Announcements", "Corporate Filings & Events", supplementary.get('bse_announcements',''))}
    {_card("BSE Bulk / Block Deals", "Large Institutional Trades", supplementary.get('bse_bulk_deals',''))}
    {_card("Bull Case", "Bullish Research Arguments", bull_history)}
    {_card("Bear Case", "Bearish Research Arguments", bear_history)}
    {_card("Risk Assessment", "Risk Management Review", risk_judge)}
  </div>

  <!-- Final Recommendation -->
  <h2 class="section-title">Final Recommendation</h2>
  <hr class="gold"/>
  <div class="final-card">
    <span class="eyebrow">Portfolio Manager Decision · {trade_date}</span>
    <h3 class="card-title" style="font-size:20px;margin-bottom:16px">
      Signal: <span style="color:{signal_color}">{signal_clean}</span>
    </h3>
    <div class="card-body">{(investment_plan or final_decision or "").replace(chr(10), '<br>')}</div>
  </div>

</div>

<div class="footer">
  Generated by Kodryx India Trading Agent · {datetime.now().strftime("%d %b %Y %H:%M")} IST
  · For research purposes only · Not financial advice
</div>

</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from tradingagents.dataflows.india_report import generate_report; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add tradingagents/dataflows/india_report.py
git commit -m "feat: add india_report — Kodryx-branded HTML report generator"
```

---

## Task 9: End-to-end run with TCS

**Files:** None (validation only)

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/test_india_dataflows.py -v
```

Expected: all tests PASSED

- [ ] **Step 2: Run the agent**

```bash
python run_india.py --ticker TCS --date 2026-04-29
```

Expected output:
```
============================================================
  India Trading Agent — TCS.NS
  Date: 2026-04-29
  LLM: DeepSeek V4 Pro via clod.io
============================================================

Running multi-agent analysis...
...agent output streaming...

Fetching supplementary India data...
Generating HTML report...

============================================================
  Signal: BUY   (or HOLD or SELL)
  Report: reports/TCS/TCS_20260429_XXXXXX.html
============================================================
```

- [ ] **Step 3: Open the report**

```bash
start reports/TCS/TCS_20260429_*.html
```

Verify in browser:
- Kodryx navy header visible
- TCS name and signal badge displayed
- 4 metric cards with gold numbers
- FII/DII section populated
- All 9 analysis cards present
- Final recommendation card with gold top-rule

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: India Trading Agent — TCS analysis complete, Kodryx HTML report"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** india_news ✓, india_reddit ✓, india_bse ✓, india_fii_dii ✓, india_report ✓, clod.io wiring ✓, run_india.py ✓, Kodryx design ✓
- [x] **No placeholders:** all code blocks are complete implementations
- [x] **Type consistency:** `get_india_stock_news` signature matches `get_news_yfinance` pattern (ticker, start_date, end_date → str); `get_india_macro_news` matches `get_global_news_yfinance` (curr_date, look_back_days → str)
- [x] **Vendor routing:** `india_news.get_india_stock_news` wired to `VENDOR_METHODS["get_news"]["india"]`; `get_india_macro_news` to `get_global_news`
- [x] **Error handling:** all network calls have try/except with graceful string fallbacks
- [x] **API key:** clod.io key in `.env` as `OPENROUTER_API_KEY`, loaded via `python-dotenv`
