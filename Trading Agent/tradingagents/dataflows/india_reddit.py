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

    bullish_kw = ["buy", "bullish", "strong", "growth", "upside", "target", "positive", "good results", "beat"]
    bearish_kw = ["sell", "bearish", "overvalued", "weak", "downside", "drop", "fall", "miss", "disappointing"]

    bull_count = bear_count = 0
    posts_str = ""
    for p in sorted(all_posts, key=lambda x: x["score"], reverse=True)[:15]:
        text = (p["title"] + " " + p["body"]).lower()
        if any(k in text for k in bullish_kw):
            bull_count += 1
        if any(k in text for k in bearish_kw):
            bear_count += 1
        posts_str += f"**[r/{p['subreddit']}]** {p['title']} (score: {p['score']})\n"
        if p["body"]:
            posts_str += f"{p['body'][:150]}...\n"
        posts_str += "\n"

    sentiment = "Neutral"
    if bull_count > bear_count * 1.5:
        sentiment = "Bullish"
    elif bear_count > bull_count * 1.5:
        sentiment = "Bearish"

    header = (
        f"## Reddit Sentiment for {base} ({start_date} to {end_date})\n\n"
        f"**Posts found:** {len(all_posts)} across r/IndiaInvestments + r/IndianStockMarket\n"
        f"**Sentiment:** {sentiment} (Bullish signals: {bull_count}, Bearish signals: {bear_count})\n\n"
        f"### Top Posts:\n\n"
    )
    return header + posts_str
