"""India-specific news fetcher using Google News RSS and ET Markets RSS."""
import xml.etree.ElementTree as ET
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
