"""Kodryx-branded HTML report generator for India Trading Agent."""
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict

import yfinance as yf


def _get_signal_color(signal: str) -> str:
    s = signal.upper()
    if "BUY" in s:
        return "#16a34a"
    elif "SELL" in s:
        return "#dc2626"
    return "#C9A24D"


def _clean_signal(signal: str) -> str:
    for word in ["BUY", "SELL", "HOLD"]:
        if word in signal.upper():
            return word
    return signal.strip()[:10]


def _fetch_metrics(ticker: str) -> Dict[str, str]:
    try:
        info = yf.Ticker(ticker).info
        cmp = info.get("currentPrice") or info.get("regularMarketPrice")
        pe = info.get("trailingPE")
        high = info.get("fiftyTwoWeekHigh")
        low = info.get("fiftyTwoWeekLow")
        name = info.get("longName", ticker)
        return {
            "name": name,
            "cmp": f"&#8377;{cmp:,.2f}" if cmp else "N/A",
            "pe": f"{pe:.1f}x" if pe else "N/A",
            "high": f"&#8377;{high:,.2f}" if high else "N/A",
            "low": f"&#8377;{low:,.2f}" if low else "N/A",
        }
    except Exception:
        return {"name": ticker, "cmp": "N/A", "pe": "N/A", "high": "N/A", "low": "N/A"}


def _check_earnings_alert(ticker: str) -> str:
    try:
        dates = yf.Ticker(ticker).earnings_dates
        if dates is None or dates.empty:
            return ""
        today = date.today()
        upcoming = [d.date() for d in dates.index if today <= d.date() <= today + timedelta(days=14)]
        if upcoming:
            return f"Earnings results expected on {upcoming[0].strftime('%d %b %Y')} — elevated volatility possible"
    except Exception:
        pass
    return ""


def _card(eyebrow: str, title: str, body: str, featured: bool = False) -> str:
    border_top = "border-top:3px solid #C9A24D;" if featured else ""
    safe_body = (body or "").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>") if body else "<em style='color:#6B7280'>No data available</em>"
    return f"""<div class="card" style="{border_top}">
  <span class="eyebrow">{eyebrow}</span>
  <div class="card-title">{title}</div>
  <div class="card-body">{safe_body}</div>
</div>"""


def _metric_card(label: str, value: str) -> str:
    return f"""<div class="metric-card">
  <div class="metric-value">{value}</div>
  <div class="metric-label">{label}</div>
</div>"""


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#fff;color:#0E2A3A;-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 24px}
.header{background:#0E2A3A;padding:18px 32px;display:flex;align-items:center;justify-content:space-between}
.header-brand{font-family:'Poppins',sans-serif;font-weight:700;font-size:22px;color:#C9A24D;letter-spacing:-0.01em}
.header-tagline{font-size:11px;color:rgba(255,255,255,0.4);margin-top:2px}
.header-right{text-align:right}
.header-sub{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(255,255,255,0.5);font-weight:600}
.header-model{font-size:12px;color:rgba(255,255,255,0.4);margin-top:3px}
.hero{padding:48px 0 32px}
.hero-eye{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:12px}
.hero-title{font-family:'Poppins',sans-serif;font-size:40px;font-weight:700;color:#0E2A3A;line-height:1.15;letter-spacing:-0.015em;margin-bottom:20px}
.signal-badge{display:inline-flex;align-items:center;gap:10px;background:#0E2A3A;font-family:'Poppins',sans-serif;font-size:22px;font-weight:700;padding:12px 32px;border-radius:999px;letter-spacing:-0.01em}
.signal-dot{width:10px;height:10px;border-radius:50%}
.earn-alert{margin-top:16px;padding:10px 16px;background:#fef9ee;border:1px solid #C9A24D;border-radius:6px;font-size:14px;color:#0E2A3A}
.metrics-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:32px 0}
.metric-card{border:1px solid #EEF0F3;border-radius:8px;padding:20px 16px;text-align:center}
.metric-value{font-family:'Poppins',sans-serif;font-size:28px;font-weight:700;color:#C9A24D;line-height:1;margin-bottom:6px}
.metric-label{font-size:13px;color:#6B7280;font-weight:500}
.fii-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:32px}
.fii-card{border:1px solid #EEF0F3;border-radius:8px;padding:16px 20px}
.fii-lbl{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:8px}
.fii-val{font-family:'Poppins',sans-serif;font-size:20px;font-weight:700;color:#0E2A3A}
hr.gold{border:0;border-top:2px solid #C9A24D;width:56px;margin:0 0 28px}
.section-title{font-family:'Poppins',sans-serif;font-size:24px;font-weight:600;color:#0E2A3A;margin-bottom:20px}
.cards-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:36px}
.card{border:1px solid #EEF0F3;border-radius:8px;padding:24px;background:#fff;transition:border-color 200ms cubic-bezier(.2,0,0,1)}
.card:hover{border-color:#C9A24D}
.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;display:block;margin-bottom:8px}
.card-title{font-family:'Poppins',sans-serif;font-size:16px;font-weight:600;color:#0E2A3A;margin-bottom:12px}
.card-body{font-size:14px;color:#0E2A3A;line-height:1.6}
.final-card{border:1px solid #D8DCE2;border-top:3px solid #C9A24D;border-radius:8px;padding:32px;margin-bottom:48px}
.final-card .card-body{font-size:15px;line-height:1.75}
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
    """Generate a Kodryx-branded HTML report. Returns the file path."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    metrics = _fetch_metrics(ticker)
    signal_clean = _clean_signal(signal)
    signal_color = _get_signal_color(signal)
    earnings_alert = _check_earnings_alert(ticker)
    base = ticker.replace(".NS", "").replace(".BO", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"{base}_{timestamp}.html")

    # Agent reports
    market_report      = final_state.get("market_report", "")
    sentiment_report   = final_state.get("sentiment_report", "")
    news_report        = final_state.get("news_report", "")
    fundamentals_report= final_state.get("fundamentals_report", "")
    inv_debate         = final_state.get("investment_debate_state", {})
    bull_history       = inv_debate.get("bull_history", "")
    bear_history       = inv_debate.get("bear_history", "")
    risk_debate        = final_state.get("risk_debate_state", {})
    risk_judge         = risk_debate.get("judge_decision", "")
    final_decision     = final_state.get("final_trade_decision", "")
    investment_plan    = final_state.get("investment_plan", "")

    # FII/DII summary lines
    fii_dii_text = supplementary.get("fii_dii", "")
    fii_line = dii_line = "Data unavailable"
    for line in fii_dii_text.split("\n"):
        if "FII/FPI Net:" in line:
            fii_line = line.replace("**FII/FPI Net:**", "").strip()
        elif "DII Net:" in line:
            dii_line = line.replace("**DII Net:**", "").strip()

    earn_html = f'<div class="earn-alert">&#9888; {earnings_alert}</div>' if earnings_alert else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>India Trading Agent &mdash; {base} &middot; {trade_date}</title>
<style>{_CSS}</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header-brand">KODRYX AI</div>
    <div class="header-tagline">Intelligence &middot; Innovation &middot; Impact</div>
  </div>
  <div class="header-right">
    <div class="header-sub">India Trading Agent</div>
    <div class="header-model">Powered by DeepSeek V4 Pro &middot; clod.io</div>
  </div>
</div>

<div class="wrap">

  <div class="hero">
    <div class="hero-eye">{base} &middot; NSE &middot; {trade_date}</div>
    <h1 class="hero-title">{metrics['name']}</h1>
    <div class="signal-badge" style="color:{signal_color}">
      <span class="signal-dot" style="background:{signal_color}"></span>
      {signal_clean}
    </div>
    {earn_html}
  </div>

  <div class="metrics-grid">
    {_metric_card("Current Market Price", metrics['cmp'])}
    {_metric_card("P/E Ratio (TTM)", metrics['pe'])}
    {_metric_card("52-Week High", metrics['high'])}
    {_metric_card("52-Week Low", metrics['low'])}
  </div>

  <h2 class="section-title">Institutional Flow</h2>
  <hr class="gold"/>
  <div class="fii-grid">
    <div class="fii-card">
      <div class="fii-lbl">FII / FPI Net Activity</div>
      <div class="fii-val">{fii_line}</div>
    </div>
    <div class="fii-card">
      <div class="fii-lbl">DII Net Activity</div>
      <div class="fii-val">{dii_line}</div>
    </div>
  </div>

  <h2 class="section-title">Agent Analysis</h2>
  <hr class="gold"/>
  <div class="cards-grid">
    {_card("Technical Analysis", "Market &amp; Price Action", market_report)}
    {_card("Fundamental Analysis", "Financials &amp; Valuation", fundamentals_report)}
    {_card("News &amp; Sentiment", "India News Coverage", news_report)}
    {_card("Social Sentiment", "Reddit &mdash; r/IndiaInvestments + r/IndianStockMarket", supplementary.get('reddit_sentiment',''))}
    {_card("BSE Announcements", "Corporate Filings &amp; Events", supplementary.get('bse_announcements',''))}
    {_card("BSE Bulk / Block Deals", "Large Institutional Trades", supplementary.get('bse_bulk_deals',''))}
    {_card("Bull Case", "Bullish Research Arguments", bull_history)}
    {_card("Bear Case", "Bearish Research Arguments", bear_history)}
    {_card("Risk Assessment", "Risk Management Review", risk_judge)}
  </div>

  <h2 class="section-title">Final Recommendation</h2>
  <hr class="gold"/>
  <div class="final-card">
    <span class="eyebrow">Portfolio Manager Decision &middot; {trade_date}</span>
    <div class="card-title" style="font-size:20px;margin-bottom:16px">
      Signal: <span style="color:{signal_color};font-family:'Poppins',sans-serif">{signal_clean}</span>
    </div>
    <div class="card-body">{(investment_plan or final_decision or "").replace(chr(10), '<br>')}</div>
  </div>

</div>

<div class="footer">
  Generated by Kodryx India Trading Agent &middot; {datetime.now().strftime("%d %b %Y %H:%M")} IST
  &middot; For research purposes only &middot; Not financial advice
</div>

</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
