"""BSE India corporate announcements and bulk deal fetcher."""
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


def _get_scrip_code(ticker: str):
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
