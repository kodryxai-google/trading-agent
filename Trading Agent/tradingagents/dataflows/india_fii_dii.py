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

        if fii_net is not None and dii_net is not None:
            if fii_net > 0 and dii_net > 0:
                implication = "Strong — both foreign and domestic institutions buying"
            elif fii_net < 0 and dii_net < 0:
                implication = "Weak — both foreign and domestic institutions selling"
            elif fii_net < 0 and dii_net > 0:
                implication = "Mixed — foreign selling, domestic support"
            else:
                implication = "Mixed — foreign buying, domestic selling"
            result += f"**Market Implication:** {implication}\n"

        return result

    except Exception as e:
        return f"FII/DII data temporarily unavailable ({e}). Requires NSE India connectivity."
