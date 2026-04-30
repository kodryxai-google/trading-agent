"""Signal cache — pre-warm Nifty 50 signals and serve from local JSON."""
import json
from datetime import date
from pathlib import Path
from typing import Any, Optional


CACHE_DIR = Path(__file__).parent.parent.parent / "reports" / "cache"


def cache_path(ticker: str, trade_date: str) -> Path:
    """Return the cache file path for a ticker+date combination."""
    base = ticker.replace(".NS", "").replace(".BO", "")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{base}_{trade_date}.json"


def read_cache(ticker: str, trade_date: str) -> Optional[dict[str, Any]]:
    """Read a cached analysis from disk, if it exists and is from today."""
    cp = cache_path(ticker, trade_date)
    if cp.exists():
        try:
            return json.loads(cp.read_text())
        except json.JSONDecodeError:
            pass
    return None


def write_cache(ticker: str, trade_date: str, final_state: dict, signal: str, supplementary: dict) -> None:
    """Write analysis results to cache."""
    cp = cache_path(ticker, trade_date)
    payload = {
        "ticker": ticker,
        "trade_date": trade_date,
        "signal": signal,
        "final_state": {
            k: v for k, v in final_state.items()
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
        },
        "supplementary": supplementary,
    }
    cp.write_text(json.dumps(payload, indent=2, default=str))


def get_cache_age(ticker: str, trade_date: str) -> Optional[str]:
    """Return a human-readable cache age, or None if not cached."""
    cp = cache_path(ticker, trade_date)
    if not cp.exists():
        return None
    return f"Cached · {date.today().isoformat()}"
