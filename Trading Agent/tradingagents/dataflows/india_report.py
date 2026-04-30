"""Kodryx-branded HTML report generator for India Trading Agent."""
import json
import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

# ---------------------------------------------------------------------------
# Issue 3 — Aggressive narration / internal-process filter
# Applied AFTER LLM generation, before ANY text reaches the report.
# ---------------------------------------------------------------------------
_NARRATION_LINE_RE = re.compile(
    r"^("
    r"(now\s+(i\s+have|let\s+me|i\s+will|i'll|i\s+can|we\s+have|i've|i\s+am))|"
    r"(let\s+me\s+(compile|analyze|analyse|now|check|look|gather|calculate|fetch|"
    r"retrieve|provide|create|write|present|summarize|summarise|begin|start|review|consider))|"
    r"(i\s+(will|am\s+going\s+to|shall|need\s+to|want\s+to|should|can\s+now)\s+"
    r"(compile|analyze|write|create|provide|calculate|fetch|retrieve|"
    r"look|check|gather|present|summarize|now))|"
    r"(compiling|analyzing|analysing|fetching|retrieving|calculating|"
    r"examining|reviewing|processing|summarizing|summarising)|"
    r"(based\s+on\s+(the\s+|all\s+|this\s+)?data\s+(above|gathered|retrieved|"
    r"collected|below|provided|shared)[\s,])|"
    r"(with\s+(all|this|the)\s+(data|information)\s+(now\s+)?"
    r"(in\s+hand|available|gathered|collected)[\s,])|"
    r"(i\s+have\s+(now\s+)?(compiled|analyzed|gathered|retrieved|calculated|"
    r"collected|reviewed|examined|completed))|"
    r"(excellent[,.]|great[,.]|perfect[,.]|alright[,.]|okay[,.]|sure[,.]|"
    r"certainly[,.]|absolutely[,.]|of\s+course[,.])"
    r")",
    re.IGNORECASE,
)

_TRANSITION_LINE_RE = re.compile(
    r"^("
    r"(here\s+is\s+(the|a|my|an|our))|"
    r"(here\s+are\s+(the|my|some))|"
    r"(below\s+(is|are)\s+(the|a|my))|"
    r"(the\s+following\s+(is|are|presents|provides))|"
    r"(as\s+(requested|follows|you\s+can\s+see|outlined|noted))|"
    r"(i\s+have\s+(compiled|analyzed|gathered|retrieved|calculated)\s+(the|a|an|this))"
    r")",
    re.IGNORECASE,
)

# Issue 9 — LaTeX sanitisation
_LATEX_SUBS = [
    (re.compile(r'\$\\searrow\$'),    '↘'),
    (re.compile(r'\$\\nearrow\$'),    '↗'),
    (re.compile(r'\$\\uparrow\$'),    '↑'),
    (re.compile(r'\$\\downarrow\$'),  '↓'),
    (re.compile(r'\$\\rightarrow\$'), '→'),
    (re.compile(r'\$\\leftarrow\$'),  '←'),
    (re.compile(r'\$\\approx\$'),     '≈'),
    (re.compile(r'\$\\geq\$'),        '≥'),
    (re.compile(r'\$\\leq\$'),        '≤'),
    (re.compile(r'\$\\pm\$'),         '±'),
    (re.compile(r'\$\\times\$'),      '×'),
    (re.compile(r'\$\\infty\$'),      '∞'),
    (re.compile(r'\$([^$\n]{1,60})\$'), r'\1'),   # strip remaining inline math
]

# Issue 4 — Tone softening map (applied when final signal is bullish)
_TONE_SOFTEN = [
    (re.compile(r'\bsevere\s+bearish\b', re.I),          'short-term bearish'),
    (re.compile(r'\bdeath\s+spiral\b', re.I),             'technical weakness'),
    (re.compile(r'\brelentless\s+selling\s+pressure\b', re.I), 'sustained selling pressure'),
    (re.compile(r'\bcatastrophic\s+(drop|decline|fall)\b', re.I), r'significant \1'),
    (re.compile(r'\bcollapse\b', re.I),                   'decline'),
    (re.compile(r'\bpanic\s+sell(ing)?\b', re.I),         'selling pressure'),
    (re.compile(r'\bfree.?fall\b', re.I),                 'downtrend'),
    (re.compile(r'\bdire\s+(outlook|situation)\b', re.I), 'challenging outlook'),
    (re.compile(r'\bdisastrous\b', re.I),                 'challenging'),
    (re.compile(r'\bdevastating\b', re.I),                'significant'),
    (re.compile(r'\bsevere\s+downturn\b', re.I),          'near-term weakness'),
]


def _sanitise(text: str, soften_tone: bool = False) -> str:
    """Strip AI narration artifacts, LaTeX, and optionally soften extreme tone."""
    if not text:
        return text

    # LaTeX → unicode
    for pat, rep in _LATEX_SUBS:
        text = pat.sub(rep, text)

    # Narration line filter
    out_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and (_NARRATION_LINE_RE.match(stripped) or _TRANSITION_LINE_RE.match(stripped)):
            continue
        out_lines.append(line)
    text = "\n".join(out_lines).strip()

    # Tone softening (only when PM says BUY/ACCUMULATE)
    if soften_tone:
        for pat, rep in _TONE_SOFTEN:
            text = pat.sub(rep, text)

    return text


# Issue 5 — Compress verbose text for Snapshot mode
def _compress(text: str, max_chars: int = 600) -> str:
    """Return a compressed version of report text for Snapshot mode."""
    text = _sanitise(text)
    if len(text) <= max_chars:
        return text
    # Keep first N chars, end at last full sentence
    truncated = text[:max_chars]
    last_period = max(truncated.rfind('. '), truncated.rfind('.\n'))
    if last_period > max_chars // 2:
        truncated = truncated[:last_period + 1]
    return truncated + " ..."


# ---------------------------------------------------------------------------
# Issue 1 — Signal arbitration: extract per-agent signals
# ---------------------------------------------------------------------------
_SIGNAL_KEYWORDS = {
    "buy":   ["strong buy", "bullish", "buy", "accumulate", "overweight", "upside"],
    "sell":  ["strong sell", "bearish", "sell", "underweight", "downside", "reduce"],
    "hold":  ["hold", "neutral", "mixed", "wait"],
}

def _extract_agent_signal(text: str) -> Optional[str]:
    """Extract BUY / SELL / HOLD from an analyst report text."""
    if not text:
        return None
    # Look for explicit "FINAL TRANSACTION PROPOSAL"
    m = re.search(r'FINAL TRANSACTION PROPOSAL[:\s*]+\*?\*?(BUY|SELL|HOLD)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Look for Rating: / Recommendation:
    m = re.search(r'(?:rating|recommendation)[:\s*]+\*?\*?(buy|sell|hold|overweight|underweight|accumulate|reduce)', text, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
        if word in ("buy", "overweight", "accumulate"):
            return "BUY"
        if word in ("sell", "underweight", "reduce"):
            return "SELL"
        return "HOLD"
    # Score keywords
    lower = text.lower()
    buy_score  = sum(lower.count(k) for k in _SIGNAL_KEYWORDS["buy"])
    sell_score = sum(lower.count(k) for k in _SIGNAL_KEYWORDS["sell"])
    hold_score = sum(lower.count(k) for k in _SIGNAL_KEYWORDS["hold"])
    if buy_score == sell_score == hold_score == 0:
        return None
    best = max(buy_score, sell_score, hold_score)
    if buy_score == best:
        return "BUY"
    if sell_score == best:
        return "SELL"
    return "HOLD"


def _arbitration_narrative(tech: Optional[str], fund: Optional[str],
                           macro: Optional[str], pm: str) -> str:
    """Return a human-readable conflict resolution sentence."""
    signals = {k: v for k, v in {"Technical": tech, "Fundamental": fund, "Macro/News": macro}.items() if v}
    if not signals:
        return ""
    conflicting = [k for k, v in signals.items() if v != pm]
    aligned     = [k for k, v in signals.items() if v == pm]

    pm_label = {"BUY": "bullish", "SELL": "bearish", "HOLD": "neutral"}.get(pm, pm.lower())

    if not conflicting:
        return f"All analytical layers are aligned: {', '.join(aligned)} support a {pm_label} stance."

    conf_str = ", ".join(f"{k} ({v})" for k, v in signals.items() if k in conflicting)
    align_str = ", ".join(f"{k} ({v})" for k, v in signals.items() if k in aligned)

    if pm in ("BUY", "ACCUMULATE"):
        return (
            f"{conf_str} signal{'s' if len(conflicting)>1 else ''} remain{'s' if len(conflicting)==1 else ''} "
            f"cautionary in the short term; however, "
            f"{align_str + ' support' if align_str else 'valuation and long-term thesis'} "
            f"override near-term technical weakness — the portfolio decision is {pm_label}."
        )
    if pm == "SELL":
        return (
            f"{conf_str} signal{'s' if len(conflicting)>1 else ''} indicate near-term resilience; "
            f"however, {align_str + ' and risk analysis' if align_str else 'risk factors'} dominate — "
            f"the portfolio decision is {pm_label}."
        )
    return (
        f"Mixed signals detected: {conf_str} diverge from {align_str or 'the portfolio view'}. "
        f"The portfolio manager adopts a {pm_label} stance pending resolution."
    )


# ---------------------------------------------------------------------------
# Issue 2 — Confidence always computed (never N/A)
# ---------------------------------------------------------------------------
def _compute_report_confidence(
    market_report: str,
    news_report: str,
    fundamentals_report: str,
    anomalies: List[str],
    computed: Dict[str, Any],
) -> int:
    """Compute confidence score — text extraction first, engine fallback."""
    from tradingagents.agents.utils.confidence import (
        infer_factors_from_reports, compute_confidence, ConfidenceFactors
    )

    # Try text extraction (structured output path)
    for src in (market_report, news_report, fundamentals_report):
        m = re.search(r'Confidence[:\s]+(\d{1,3})%', src or "", re.IGNORECASE)
        if m:
            return int(m.group(1))

    # Engine fallback — always produces a number
    factors = infer_factors_from_reports(
        market_report=market_report,
        news_report=news_report,
        fundamentals_report=fundamentals_report,
        anomaly_flags=anomalies,
    )

    # Enrich with precomputed MA signals (Issue 3 — no LLM arithmetic)
    if computed.get("price_above_sma50") is not None:
        factors.above_50sma = computed["price_above_sma50"]

    # Data quality penalty — beta sanity check (Issue 7)
    beta = computed.get("beta")
    if beta is not None and (beta < 0.05 or beta > 4.0):
        factors.data_inconsistency = True

    return compute_confidence(factors)


# ---------------------------------------------------------------------------
# Issue 7 — Fundamentals sanity checks
# ---------------------------------------------------------------------------
_FUNDAMENTAL_RANGES = {
    "beta":          (0.05, 4.0,   "Beta"),
    "pe":            (0.5,  200.0, "P/E Ratio"),
    "div_yield":     (0.0,  0.30,  "Dividend Yield"),
}

def _validate_fundamentals(cs: Dict[str, Any]) -> List[str]:
    """Return list of suspicious metric warnings."""
    warnings = []
    for key, (lo, hi, label) in _FUNDAMENTAL_RANGES.items():
        val = cs.get(key)
        if val is not None and (val < lo or val > hi):
            warnings.append(f"{label} = {val:.3f} is outside expected range [{lo}, {hi}] — treat with caution")
    return warnings


# ---------------------------------------------------------------------------
# Issue 2 / 6 — Confidence meta
# ---------------------------------------------------------------------------
def _confidence_meta(score: int) -> Tuple[str, str]:
    if score >= 80: return "High",     "#16a34a"
    if score >= 60: return "Moderate", "#C9A24D"
    if score >= 40: return "Weak",     "#ea580c"
    return "Uncertain", "#dc2626"


# ---------------------------------------------------------------------------
# Issue 2 & 4 — Canonical signal mapping
# ---------------------------------------------------------------------------
_SIGNAL_MAP = {
    "buy":         ("BUY",       "#16a34a", "bullish"),
    "overweight":  ("ACCUMULATE","#22c55e", "bullish"),
    "hold":        ("HOLD",      "#C9A24D", "neutral"),
    "underweight": ("REDUCE",    "#ea580c", "bearish"),
    "sell":        ("SELL",      "#dc2626", "bearish"),
}

def _resolve_signal(raw: str) -> Tuple[str, str, str]:
    key = raw.strip().lower()
    if key.startswith("underweigh"): key = "underweight"  # typo guard
    return _SIGNAL_MAP.get(key, _SIGNAL_MAP.get(
        next((r for r in ("sell","underweight","buy","overweight","hold") if r in key), "hold")
    ))


# ---------------------------------------------------------------------------
# Issue 3 — Precompute numeric signals + chart data
# ---------------------------------------------------------------------------
def _fetch_computed_signals(ticker: str) -> Dict[str, Any]:
    result = {
        "name": ticker, "cmp": None, "pe": None, "high_52w": None, "low_52w": None,
        "sma50": None, "sma200": None, "ema10": None, "beta": None, "div_yield": None,
        "ema10_above_sma50": None, "price_above_sma50": None,
        "price_above_sma200": None, "sma50_above_sma200": None,
        "trend": "Neutral", "momentum": "Neutral",
        "chart_dates": [], "chart_close": [],
        "chart_sma50": [], "chart_sma200": [], "chart_ema10": [],
        "chart_rsi": [], "chart_macd": [], "chart_macd_signal": [],
    }
    try:
        t    = yf.Ticker(ticker)
        info = t.info
        result["name"]      = info.get("longName", ticker)
        result["cmp"]       = info.get("currentPrice") or info.get("regularMarketPrice")
        result["pe"]        = info.get("trailingPE")
        result["high_52w"]  = info.get("fiftyTwoWeekHigh")
        result["low_52w"]   = info.get("fiftyTwoWeekLow")
        result["sma50"]     = info.get("fiftyDayAverage")
        result["sma200"]    = info.get("twoHundredDayAverage")
        result["beta"]      = info.get("beta")
        result["div_yield"] = info.get("dividendYield")

        hist = t.history(period="6mo")
        if hist.empty:
            return result

        import pandas as pd
        cl = hist["Close"]

        # Moving averages
        sma50_s  = cl.rolling(50,  min_periods=1).mean()
        sma200_s = cl.rolling(200, min_periods=1).mean()
        ema10_s  = cl.ewm(span=10, adjust=False).mean()

        # RSI
        delta = cl.diff()
        gain  = delta.clip(lower=0).rolling(14, min_periods=1).mean()
        loss  = (-delta.clip(upper=0)).rolling(14, min_periods=1).mean()
        rs    = gain / loss.replace(0, float("nan"))
        rsi_s = 100 - (100 / (1 + rs))

        # MACD
        ema12    = cl.ewm(span=12, adjust=False).mean()
        ema26    = cl.ewm(span=26, adjust=False).mean()
        macd_s   = ema12 - ema26
        signal_s = macd_s.ewm(span=9, adjust=False).mean()

        # Precomputed booleans — never inferred by LLM
        last_ema10  = float(ema10_s.iloc[-1])
        last_sma50  = float(sma50_s.iloc[-1])
        last_sma200 = float(sma200_s.iloc[-1])
        last_cmp    = result["cmp"] or float(cl.iloc[-1])

        result["ema10"]               = last_ema10
        result["sma50"]               = result["sma50"] or last_sma50
        result["sma200"]              = result["sma200"] or last_sma200
        result["ema10_above_sma50"]   = last_ema10  > last_sma50
        result["price_above_sma50"]   = last_cmp    > last_sma50
        result["price_above_sma200"]  = last_cmp    > last_sma200
        result["sma50_above_sma200"]  = last_sma50  > last_sma200

        pa200 = result["price_above_sma200"]
        s5200 = result["sma50_above_sma200"]
        result["trend"]    = "Bullish" if (pa200 and s5200) else "Bearish" if (not pa200 and not s5200) else "Mixed"
        result["momentum"] = "Strengthening" if last_ema10 > last_sma50 else "Weakening"

        # Chart data — last 90 trading days
        tail = hist.tail(90)
        fmt  = "%d %b"
        result["chart_dates"]       = [d.strftime(fmt) for d in tail.index]
        result["chart_close"]       = [round(float(v), 2) for v in tail["Close"]]
        result["chart_sma50"]       = [round(float(v), 2) for v in sma50_s.tail(90)]
        result["chart_sma200"]      = [round(float(v), 2) for v in sma200_s.tail(90)]
        result["chart_ema10"]       = [round(float(v), 2) for v in ema10_s.tail(90)]
        result["chart_rsi"]         = [round(float(v), 2) for v in rsi_s.tail(90)]
        result["chart_macd"]        = [round(float(v), 2) for v in macd_s.tail(90)]
        result["chart_macd_signal"] = [round(float(v), 2) for v in signal_s.tail(90)]

    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------
def _build_html_table(rows: list) -> str:
    if len(rows) < 2:
        return ""
    cols = [c.strip() for c in rows[0].strip("|").split("|")]
    has_header = len(rows) > 1 and re.match(r'^\|[\s\-:|]+\|$', rows[1].strip())
    data_start = 2 if has_header else 0
    html = '<table style="width:100%;border-collapse:collapse;font-size:12px;margin:10px 0"><thead><tr>'
    if has_header:
        for c in cols:
            html += f'<th style="text-align:left;padding:8px 10px;border-bottom:2px solid #C9A24D;font-weight:600;color:#0E2A3A;background:#F7F8FA">{_inline(c)}</th>'
        html += '</tr></thead><tbody>'
        for row in rows[data_start:]:
            cells = [c.strip() for c in row.strip("|").split("|")]
            html += '<tr>' + ''.join(f'<td style="padding:8px 10px;border-bottom:1px solid #EEF0F3;vertical-align:top">{_inline(c)}</td>' for c in cells) + '</tr>'
    html += '</tbody></table>'
    return html


def _inline(text: str) -> str:
    for pat, rep in _LATEX_SUBS:
        text = pat.sub(rep, text)
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*',     r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',         r'<em>\1</em>', text)
    text = re.sub(r'`(.+?)`', r'<code style="background:#F3F4F6;padding:1px 4px;border-radius:3px;font-size:11px">\1</code>', text)
    return text


def _md_to_html(text: str, soften: bool = False) -> str:
    if not text:
        return "<em style='color:#6B7280'>No data available</em>"
    text = _sanitise(text, soften_tone=soften)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        line    = lines[i]
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            trows = []
            while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                trows.append(lines[i]); i += 1
            if len(trows) >= 2:
                out.append(_build_html_table(trows)); continue
            else:
                i -= len(trows)
        if   line.startswith("### "): out.append(f'<h4 style="font-size:13px;font-weight:600;color:#0E2A3A;margin:14px 0 4px">{_inline(line[4:])}</h4>')
        elif line.startswith("## "):  out.append(f'<h3 style="font-size:14px;font-weight:700;color:#0E2A3A;margin:16px 0 6px">{_inline(line[3:])}</h3>')
        elif line.startswith("# "):   out.append(f'<h2 style="font-size:15px;font-weight:700;color:#0E2A3A;margin:16px 0 6px">{_inline(line[2:])}</h2>')
        elif re.match(r'^[-*_]{3,}$', stripped): out.append('<hr style="border:0;border-top:1px solid #EEF0F3;margin:10px 0">')
        elif re.match(r'^[-*•] ', line): out.append(f'<li style="margin-bottom:3px">{_inline(line[2:])}</li>')
        elif re.match(r'^\d+\. ', line): out.append(f'<li style="margin-bottom:3px">{_inline(re.sub(chr(92)+"d+"+chr(46)+" ","",line,1))}</li>')
        elif stripped == "":           out.append('<div style="height:6px"></div>')
        else:                          out.append(f'<p style="margin:0 0 4px">{_inline(line)}</p>')
        i += 1
    html = "\n".join(out)
    html = re.sub(r'(<li[^>]*>.*?</li>\n?)+', lambda m: f'<ul style="padding-left:18px;margin:4px 0">{m.group(0)}</ul>', html, flags=re.DOTALL)
    return html


def _fmt_inr(val) -> str:
    return f"&#8377;{val:,.2f}" if val else "N/A"

def _pill(val: Optional[bool], t: str, f: str) -> str:
    if val is True:  return f'<span class="pill bull">{t}</span>'
    if val is False: return f'<span class="pill bear">{f}</span>'
    return '<span class="pill neutral">N/A</span>'

def _check_earnings_alert(ticker: str) -> str:
    try:
        dates = yf.Ticker(ticker).earnings_dates
        if dates is None or dates.empty: return ""
        today = date.today()
        upcoming = [d.date() for d in dates.index if today <= d.date() <= today + timedelta(days=14)]
        if upcoming:
            return f"Earnings results expected on {upcoming[0].strftime('%d %b %Y')} — elevated volatility possible"
    except Exception: pass
    return ""

def _metric_card(label: str, value: str, color: str = "#C9A24D") -> str:
    return (f'<div class="metric-card">'
            f'<div class="metric-value" style="color:{color}">{value}</div>'
            f'<div class="metric-label">{label}</div></div>')

def _card(eyebrow: str, title: str, body: str, accent: str = "", soften: bool = False) -> str:
    border = f"border-top:3px solid {accent};" if accent else ""
    return (f'<div class="card" style="{border}">'
            f'<span class="eyebrow">{eyebrow}</span>'
            f'<div class="card-title">{title}</div>'
            f'<div class="card-body">{_md_to_html(body, soften=soften)}</div></div>')


# ---------------------------------------------------------------------------
# Issue 6 — Chart.js chart blocks
# ---------------------------------------------------------------------------
def _build_charts(cs: Dict[str, Any], signal_color: str) -> str:
    if not cs["chart_dates"]:
        return ""
    labels      = json.dumps(cs["chart_dates"])
    closes      = json.dumps(cs["chart_close"])
    sma50       = json.dumps(cs["chart_sma50"])
    sma200      = json.dumps(cs["chart_sma200"])
    ema10       = json.dumps(cs["chart_ema10"])
    rsi         = json.dumps(cs["chart_rsi"])
    macd        = json.dumps(cs["chart_macd"])
    macd_signal = json.dumps(cs["chart_macd_signal"])

    return f"""
<div style="margin:32px 0">
  <h2 class="section-title">Price &amp; Indicator Charts</h2>
  <hr class="gold"/>

  <!-- Price + MA chart -->
  <div style="background:#F7F8FA;border:1px solid #EEF0F3;border-radius:8px;padding:20px;margin-bottom:16px">
    <div style="font-size:12px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">Price with Moving Averages (90 days)</div>
    <canvas id="priceChart" height="80"></canvas>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px">
    <!-- RSI chart -->
    <div style="background:#F7F8FA;border:1px solid #EEF0F3;border-radius:8px;padding:20px">
      <div style="font-size:12px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">RSI (14)</div>
      <canvas id="rsiChart" height="120"></canvas>
    </div>
    <!-- MACD chart -->
    <div style="background:#F7F8FA;border:1px solid #EEF0F3;border-radius:8px;padding:20px">
      <div style="font-size:12px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px">MACD (12,26,9)</div>
      <canvas id="macdChart" height="120"></canvas>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
const lbl={labels};
const C={{
  defaultColor:'{signal_color}',
  sma50:'#C9A24D',sma200:'#6B7280',ema10:'#3b82f6',
  rsiLine:'#8b5cf6',overbought:'rgba(220,38,38,0.15)',oversold:'rgba(22,163,74,0.15)',
  macd:'#0E2A3A',macdSig:'#dc2626'
}};
const gridOpts={{color:'rgba(0,0,0,0.04)'}};
const tickOpts={{color:'#9CA3AF',font:{{size:10}}}};

// Price chart
new Chart(document.getElementById('priceChart'),{{
  type:'line',
  data:{{
    labels:lbl,
    datasets:[
      {{label:'Close',data:{closes},borderColor:C.defaultColor,borderWidth:2,pointRadius:0,fill:false,tension:0.3}},
      {{label:'50-SMA',data:{sma50},borderColor:C.sma50,borderWidth:1.5,borderDash:[4,2],pointRadius:0,fill:false,tension:0.3}},
      {{label:'200-SMA',data:{sma200},borderColor:C.sma200,borderWidth:1.5,borderDash:[2,4],pointRadius:0,fill:false,tension:0.3}},
      {{label:'10-EMA',data:{ema10},borderColor:C.ema10,borderWidth:1,pointRadius:0,fill:false,tension:0.3}},
    ]
  }},
  options:{{
    responsive:true,animation:false,
    plugins:{{legend:{{labels:{{font:{{size:11}},color:'#0E2A3A'}}}},tooltip:{{mode:'index',intersect:false}}}},
    scales:{{
      x:{{ticks:{{...tickOpts,maxTicksLimit:10,maxRotation:0}},grid:gridOpts}},
      y:{{ticks:tickOpts,grid:gridOpts}}
    }}
  }}
}});

// RSI chart
new Chart(document.getElementById('rsiChart'),{{
  type:'line',
  data:{{
    labels:lbl,
    datasets:[
      {{label:'RSI',data:{rsi},borderColor:C.rsiLine,borderWidth:1.5,pointRadius:0,fill:false,tension:0.3}},
    ]
  }},
  options:{{
    responsive:true,animation:false,
    plugins:{{legend:{{display:false}},tooltip:{{mode:'index',intersect:false}},
      annotation:{{}}
    }},
    scales:{{
      x:{{ticks:{{...tickOpts,maxTicksLimit:8,maxRotation:0}},grid:gridOpts}},
      y:{{min:0,max:100,ticks:{{...tickOpts,stepSize:20}},grid:gridOpts}}
    }}
  }}
}});

// MACD chart
new Chart(document.getElementById('macdChart'),{{
  type:'line',
  data:{{
    labels:lbl,
    datasets:[
      {{label:'MACD',data:{macd},borderColor:C.macd,borderWidth:1.5,pointRadius:0,fill:false,tension:0.3}},
      {{label:'Signal',data:{macd_signal},borderColor:C.macdSig,borderWidth:1.5,borderDash:[3,2],pointRadius:0,fill:false,tension:0.3}},
    ]
  }},
  options:{{
    responsive:true,animation:false,
    plugins:{{legend:{{labels:{{font:{{size:10}},color:'#0E2A3A'}}}},tooltip:{{mode:'index',intersect:false}}}},
    scales:{{
      x:{{ticks:{{...tickOpts,maxTicksLimit:8,maxRotation:0}},grid:gridOpts}},
      y:{{ticks:tickOpts,grid:gridOpts}}
    }}
  }}
}});
</script>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
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
.hero{padding:36px 0 20px}
.hero-eye{font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:10px}
.hero-title{font-family:'Poppins',sans-serif;font-size:34px;font-weight:700;color:#0E2A3A;line-height:1.15;letter-spacing:-0.015em;margin-bottom:16px}
.signal-badge{display:inline-flex;align-items:center;gap:10px;background:#0E2A3A;font-family:'Poppins',sans-serif;font-size:20px;font-weight:700;padding:10px 28px;border-radius:999px;margin-right:10px}
.signal-dot{width:10px;height:10px;border-radius:50%}
.conf-badge{display:inline-flex;align-items:center;gap:8px;border:2px solid currentColor;font-family:'Poppins',sans-serif;font-size:15px;font-weight:700;padding:8px 18px;border-radius:999px}
.earn-alert{margin-top:12px;padding:10px 14px;background:#fef9ee;border:1px solid #C9A24D;border-radius:6px;font-size:13px}
/* Executive summary */
.exec-summary{background:#F7F8FA;border:1px solid #EEF0F3;border-left:4px solid #C9A24D;border-radius:8px;padding:20px 24px;margin:20px 0 28px}
.exec-title{font-size:11px;font-weight:700;color:#6B7280;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:14px}
.exec-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}
.exec-label{font-size:10px;text-transform:uppercase;letter-spacing:0.06em;color:#9CA3AF;font-weight:600;margin-bottom:3px}
.exec-value{font-family:'Poppins',sans-serif;font-size:14px;font-weight:700;color:#0E2A3A}
/* Signal arbitration */
.arbitration{background:#fff;border:1px solid #EEF0F3;border-left:4px solid #3b82f6;border-radius:8px;padding:16px 20px;margin-bottom:24px}
.arb-title{font-size:11px;font-weight:700;color:#3b82f6;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px}
.arb-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}
.arb-cell{border:1px solid #EEF0F3;border-radius:6px;padding:10px 12px;text-align:center}
.arb-label{font-size:10px;color:#9CA3AF;font-weight:600;text-transform:uppercase;margin-bottom:4px}
.arb-val{font-family:'Poppins',sans-serif;font-size:13px;font-weight:700}
/* Metrics */
.metrics-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:24px 0}
.metric-card{border:1px solid #EEF0F3;border-radius:8px;padding:18px 14px;text-align:center}
.metric-value{font-family:'Poppins',sans-serif;font-size:24px;font-weight:700;line-height:1;margin-bottom:5px}
.metric-label{font-size:12px;color:#6B7280;font-weight:500}
.pill{display:inline-block;padding:3px 9px;border-radius:4px;font-size:11px;font-weight:600}
.pill.bull{background:#dcfce7;color:#166534}
.pill.bear{background:#fee2e2;color:#991b1b}
.pill.neutral{background:#F3F4F6;color:#6B7280}
.signal-bar{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 20px}
.fii-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:28px}
.fii-card{border:1px solid #EEF0F3;border-radius:8px;padding:14px 18px}
.fii-lbl{font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:6px}
.fii-val{font-family:'Poppins',sans-serif;font-size:18px;font-weight:700}
hr.gold{border:0;border-top:2px solid #C9A24D;width:56px;margin:0 0 20px}
.section-title{font-family:'Poppins',sans-serif;font-size:21px;font-weight:600;color:#0E2A3A;margin-bottom:14px}
.cards-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:32px}
.card{border:1px solid #EEF0F3;border-radius:8px;padding:22px;background:#fff;transition:border-color 200ms}
.card:hover{border-color:#C9A24D}
.eyebrow{font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;display:block;margin-bottom:6px}
.card-title{font-family:'Poppins',sans-serif;font-size:15px;font-weight:600;color:#0E2A3A;margin-bottom:10px}
.card-body{font-size:13px;color:#0E2A3A;line-height:1.65}
.final-card{border:1px solid #D8DCE2;border-top:4px solid #C9A24D;border-radius:8px;padding:28px;margin-bottom:40px}
.anomaly-banner{background:#fff7ed;border:1px solid #fb923c;border-left:4px solid #ea580c;border-radius:8px;padding:14px 18px;margin-bottom:20px}
.anomaly-title{font-weight:700;color:#9a3412;margin-bottom:6px;font-size:11px;text-transform:uppercase;letter-spacing:0.06em}
.data-warn{background:#fef9ee;border:1px solid #C9A24D;border-left:4px solid #C9A24D;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:12px;color:#92400e}
.mode-bar{display:flex;gap:0;border:1px solid #EEF0F3;border-radius:8px;overflow:hidden;margin-bottom:28px;width:fit-content}
.mode-btn{padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer;background:#fff;color:#6B7280;border:none;border-right:1px solid #EEF0F3;font-family:'Poppins',sans-serif;transition:background 150ms}
.mode-btn:last-child{border-right:none}
.mode-btn.active{background:#0E2A3A;color:#C9A24D}
.mode-section{display:none}.mode-section.visible{display:block}
.footer{background:#F7F8FA;border-top:1px solid #EEF0F3;padding:20px;text-align:center;font-size:12px;color:#6B7280;margin-top:36px}
"""

_MODE_JS = """<script>
function setMode(m){
  document.querySelectorAll('.mode-section').forEach(s=>s.classList.remove('visible'));
  document.querySelectorAll('.mode-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('mode-'+m).classList.add('visible');
  document.getElementById('btn-'+m).classList.add('active');
}
document.addEventListener('DOMContentLoaded',()=>setMode('snapshot'));
</script>"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def generate_report(
    ticker: str,
    trade_date: str,
    final_state: Dict[str, Any],
    signal: str,
    supplementary: Dict[str, str],
    output_dir: str = "reports",
    data_anomalies: List[str] | None = None,
) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    anomalies = data_anomalies or []
    base      = ticker.replace(".NS", "").replace(".BO", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath  = os.path.join(output_dir, f"{base}_{timestamp}.html")

    # Signal resolution (Issue 2 & 4)
    retail_label, signal_color, sentiment = _resolve_signal(signal)
    is_bullish = sentiment == "bullish"

    # Precomputed signals (Issue 3)
    cs = _fetch_computed_signals(ticker)

    # Issue 7 — fundamentals sanity
    fund_warnings = _validate_fundamentals(cs)

    earnings_alert = _check_earnings_alert(ticker)

    # Raw reports
    raw_market      = final_state.get("market_report", "")
    raw_fundamentals= final_state.get("fundamentals_report", "")
    raw_news        = final_state.get("news_report", "")
    raw_sentiment   = final_state.get("sentiment_report", "")
    inv_debate      = final_state.get("investment_debate_state", {})
    raw_bull        = inv_debate.get("bull_history", "")
    raw_bear        = inv_debate.get("bear_history", "")
    risk_debate     = final_state.get("risk_debate_state", {})
    raw_risk        = risk_debate.get("judge_decision", "")
    raw_final       = final_state.get("final_trade_decision", "")
    raw_plan        = final_state.get("investment_plan", "")

    # Issue 1 — per-agent signal extraction for arbitration
    tech_sig  = _extract_agent_signal(raw_market)
    fund_sig  = _extract_agent_signal(raw_fundamentals)
    macro_sig = _extract_agent_signal(raw_news)
    pm_sig    = retail_label  # the authoritative decision

    arb_narrative = _arbitration_narrative(tech_sig, fund_sig, macro_sig, pm_sig)

    def _sig_color(s: Optional[str]) -> str:
        if s == "BUY":  return "#16a34a"
        if s == "SELL": return "#dc2626"
        if s == "HOLD": return "#C9A24D"
        return "#9CA3AF"

    arb_html = f"""
<div class="arbitration">
  <div class="arb-title">Signal Arbitration Dashboard</div>
  <div class="arb-grid">
    <div class="arb-cell">
      <div class="arb-label">Technical</div>
      <div class="arb-val" style="color:{_sig_color(tech_sig)}">{tech_sig or 'N/A'}</div>
    </div>
    <div class="arb-cell">
      <div class="arb-label">Fundamental</div>
      <div class="arb-val" style="color:{_sig_color(fund_sig)}">{fund_sig or 'N/A'}</div>
    </div>
    <div class="arb-cell">
      <div class="arb-label">Macro / News</div>
      <div class="arb-val" style="color:{_sig_color(macro_sig)}">{macro_sig or 'N/A'}</div>
    </div>
    <div class="arb-cell" style="border-color:#C9A24D;background:#FFFBF0">
      <div class="arb-label">Portfolio Decision</div>
      <div class="arb-val" style="color:{signal_color}">{pm_sig}</div>
    </div>
  </div>
  {f'<p style="font-size:13px;color:#374151;line-height:1.6">{arb_narrative}</p>' if arb_narrative else ''}
</div>"""

    # Issue 2 — confidence always computed
    confidence_score = _compute_report_confidence(
        raw_market, raw_news, raw_fundamentals, anomalies, cs
    )
    conf_label, conf_color = _confidence_meta(confidence_score)
    conf_display = f"{confidence_score}%"

    # Sanitised report text (Issue 3 & 4)
    market_report       = _sanitise(raw_market,       soften_tone=is_bullish)
    fundamentals_report = _sanitise(raw_fundamentals, soften_tone=False)
    news_report         = _sanitise(raw_news,         soften_tone=False)
    sentiment_report    = _sanitise(raw_sentiment,    soften_tone=False)
    bull_history        = _sanitise(raw_bull,         soften_tone=False)
    bear_history        = _sanitise(raw_bear,         soften_tone=False)
    risk_judge          = _sanitise(raw_risk,         soften_tone=False)
    final_decision      = _sanitise(raw_final,        soften_tone=False)
    investment_plan     = _sanitise(raw_plan,         soften_tone=False)

    # FII/DII
    fii_text = supplementary.get("fii_dii", "")
    fii_line = dii_line = "Data unavailable"
    inst_flow = "Mixed"
    for ln in fii_text.split("\n"):
        if "FII/FPI Net:" in ln:  fii_line = ln.replace("**FII/FPI Net:**", "").strip()
        elif "DII Net:" in ln:     dii_line = ln.replace("**DII Net:**", "").strip()
    if "selling" in fii_line.lower() and "selling" in dii_line.lower(): inst_flow = "Negative"
    elif "buying" in fii_line.lower() or "buying" in dii_line.lower():  inst_flow = "Positive"

    # Helpers for coloring
    def _trend_color(t: str) -> str:
        return "#16a34a" if t=="Bullish" else "#dc2626" if t=="Bearish" else "#C9A24D"
    def _mom_color(m: str) -> str:
        return "#16a34a" if m=="Strengthening" else "#ea580c"
    def _flow_color(f: str) -> str:
        return "#16a34a" if f=="Positive" else "#dc2626" if f=="Negative" else "#C9A24D"

    earn_html = f'<div class="earn-alert">&#9888; {earnings_alert}</div>' if earnings_alert else ""

    # Anomaly banner
    anomaly_html = ""
    if anomalies:
        items = "".join(f"<li>&#9888; {a}</li>" for a in anomalies)
        anomaly_html = (f'<div class="anomaly-banner">'
                        f'<div class="anomaly-title">Data Anomaly Flags ({len(anomalies)})</div>'
                        f'<ul style="padding-left:18px;font-size:12px;color:#7c2d12">{items}</ul></div>')

    # Issue 7 — data quality warnings
    data_warn_html = ""
    if fund_warnings:
        items = "".join(f"<div>&#9888; {w}</div>" for w in fund_warnings)
        data_warn_html = f'<div class="data-warn"><strong>Data Quality Notice:</strong> {items}</div>'

    # MA pills
    signal_bar = (
        f'{_pill(cs["price_above_sma50"],  "Price > 50-SMA",  "Price < 50-SMA")}&nbsp;'
        f'{_pill(cs["price_above_sma200"], "Price > 200-SMA", "Price < 200-SMA")}&nbsp;'
        f'{_pill(cs["ema10_above_sma50"],  "10-EMA > 50-SMA", "10-EMA < 50-SMA")}&nbsp;'
        f'{_pill(cs["sma50_above_sma200"], "Golden Cross",    "Death Cross")}'
    )

    # Charts (Issue 6)
    charts_html = _build_charts(cs, signal_color)

    # Exec summary
    exec_html = f"""
<div class="exec-summary">
  <div class="exec-title">Market Summary &mdash; {base} &middot; {trade_date}</div>
  <div class="exec-grid">
    <div><div class="exec-label">Recommendation</div><div class="exec-value" style="color:{signal_color}">{retail_label}</div></div>
    <div><div class="exec-label">AI Confidence</div><div class="exec-value" style="color:{conf_color}">{conf_display}</div></div>
    <div><div class="exec-label">Reliability</div><div class="exec-value" style="color:{conf_color}">{conf_label}</div></div>
    <div><div class="exec-label">Trend</div><div class="exec-value" style="color:{_trend_color(cs['trend'])}">{cs['trend']}</div></div>
    <div><div class="exec-label">Momentum</div><div class="exec-value" style="color:{_mom_color(cs['momentum'])}">{cs['momentum']}</div></div>
    <div><div class="exec-label">Inst. Flow</div><div class="exec-value" style="color:{_flow_color(inst_flow)}">{inst_flow}</div></div>
  </div>
</div>"""

    # Snapshot card
    snapshot_html = f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px">
  <div style="border:1px solid #EEF0F3;border-radius:10px;padding:24px">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:14px">Signal Summary</div>
    {"".join(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #F3F4F6"><span style="color:#6B7280;font-size:13px;font-weight:500">{k}</span><span style="font-weight:700;font-size:13px;color:{vc}">{vv}</span></div>' for k,vv,vc in [
        ("Recommendation", retail_label, signal_color),
        ("AI Confidence", f"{conf_display} ({conf_label})", conf_color),
        ("Trend", cs['trend'], _trend_color(cs['trend'])),
        ("Momentum", cs['momentum'], _mom_color(cs['momentum'])),
        ("Inst. Flow", inst_flow, _flow_color(inst_flow)),
        ("52W Support", _fmt_inr(cs['low_52w']), "#0E2A3A"),
        ("52W Resistance", _fmt_inr(cs['high_52w']), "#0E2A3A"),
    ])}
  </div>
  <div style="border:1px solid #EEF0F3;border-radius:10px;padding:24px">
    <div style="font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#6B7280;font-weight:600;margin-bottom:12px">Precomputed Price Signals</div>
    <div style="display:flex;flex-direction:column;gap:8px">{signal_bar.replace("&nbsp;","")}</div>
    <div style="margin-top:16px;padding-top:14px;border-top:1px solid #F3F4F6">
      <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px">Current Price</div>
      <div style="font-family:'Poppins',sans-serif;font-size:26px;font-weight:700">{_fmt_inr(cs['cmp'])}</div>
      <div style="font-size:11px;color:#9CA3AF;margin-top:4px">50-SMA: {_fmt_inr(cs['sma50'])} &nbsp;|&nbsp; 200-SMA: {_fmt_inr(cs['sma200'])}</div>
    </div>
  </div>
</div>
<div class="final-card" style="margin-top:0">
  <span class="eyebrow">Portfolio Manager Decision &middot; {trade_date}</span>
  <div class="card-title" style="font-size:17px;margin-bottom:8px">
    <span style="color:{signal_color}">{retail_label}</span>
    &nbsp;&middot;&nbsp;<span style="font-size:13px;color:{conf_color}">{conf_display} ({conf_label})</span>
  </div>
  <div class="card-body" style="margin-top:10px">{_md_to_html(_compress(investment_plan or final_decision or "", 800), soften=is_bullish)}</div>
</div>"""

    # Final body for Pro/Deep
    final_body = _md_to_html(investment_plan or final_decision or "", soften=is_bullish)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Kodryx &mdash; {base} &middot; {trade_date}</title>
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
    <div class="header-model">Powered by Gemini 2.5 Flash &middot; Google</div>
  </div>
</div>

<div class="wrap">

  <div class="hero">
    <div class="hero-eye">{base} &middot; NSE &middot; {trade_date}</div>
    <h1 class="hero-title">{cs['name']}</h1>
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <div class="signal-badge" style="color:{signal_color}">
        <span class="signal-dot" style="background:{signal_color}"></span>
        {retail_label}
      </div>
      <div class="conf-badge" style="color:{conf_color}">
        {conf_display} &nbsp; {conf_label}
      </div>
    </div>
    {earn_html}
  </div>

  {anomaly_html}
  {data_warn_html}
  {exec_html}
  {arb_html}

  <div class="mode-bar">
    <button class="mode-btn" id="btn-snapshot" onclick="setMode('snapshot')">Snapshot</button>
    <button class="mode-btn" id="btn-pro"      onclick="setMode('pro')">Pro Report</button>
    <button class="mode-btn" id="btn-deep"     onclick="setMode('deep')">Deep Institutional</button>
  </div>

  <!-- SNAPSHOT -->
  <div class="mode-section" id="mode-snapshot">
    {snapshot_html}
  </div>

  <!-- PRO REPORT -->
  <div class="mode-section" id="mode-pro">
    <div class="metrics-grid">
      {_metric_card("Current Price", _fmt_inr(cs['cmp']), signal_color)}
      {_metric_card("P/E Ratio (TTM)", f"{cs['pe']:.1f}x" if cs['pe'] else "N/A")}
      {_metric_card("52-Week High", _fmt_inr(cs['high_52w']))}
      {_metric_card("52-Week Low", _fmt_inr(cs['low_52w']))}
    </div>
    <div class="signal-bar">{signal_bar}</div>
    {charts_html}
    <h2 class="section-title">Institutional Flow</h2>
    <hr class="gold"/>
    <div class="fii-grid">
      <div class="fii-card"><div class="fii-lbl">FII / FPI Net</div><div class="fii-val">{fii_line}</div></div>
      <div class="fii-card"><div class="fii-lbl">DII Net</div><div class="fii-val">{dii_line}</div></div>
    </div>
    <h2 class="section-title">Agent Analysis</h2>
    <hr class="gold"/>
    <div class="cards-grid">
      {_card("Technical Analysis", "Market &amp; Price Action", market_report, signal_color, is_bullish)}
      {_card("Fundamental Analysis", "Financials &amp; Valuation", fundamentals_report)}
      {_card("News &amp; Macro", "India &amp; Global Coverage", news_report)}
      {_card("Social Sentiment", "Reddit &mdash; India Investing", supplementary.get('reddit_sentiment',''))}
      {_card("BSE Announcements", "Corporate Filings", supplementary.get('bse_announcements',''))}
      {_card("BSE Bulk Deals", "Large Institutional Trades", supplementary.get('bse_bulk_deals',''))}
    </div>
    <h2 class="section-title">Final Recommendation</h2>
    <hr class="gold"/>
    <div class="final-card">
      <span class="eyebrow">Portfolio Manager Decision &middot; {trade_date}</span>
      <div class="card-title" style="font-size:17px;margin-bottom:8px">
        <span style="color:{signal_color}">{retail_label}</span>&nbsp;&middot;&nbsp;
        <span style="font-size:13px;color:{conf_color}">{conf_display} ({conf_label})</span>
      </div>
      <div class="card-body" style="margin-top:10px">{final_body}</div>
    </div>
  </div>

  <!-- DEEP INSTITUTIONAL -->
  <div class="mode-section" id="mode-deep">
    <div class="metrics-grid">
      {_metric_card("Current Price", _fmt_inr(cs['cmp']), signal_color)}
      {_metric_card("P/E Ratio (TTM)", f"{cs['pe']:.1f}x" if cs['pe'] else "N/A")}
      {_metric_card("52-Week High", _fmt_inr(cs['high_52w']))}
      {_metric_card("52-Week Low", _fmt_inr(cs['low_52w']))}
    </div>
    <div class="signal-bar">{signal_bar}</div>
    {charts_html}
    <h2 class="section-title">Institutional Flow</h2>
    <hr class="gold"/>
    <div class="fii-grid">
      <div class="fii-card"><div class="fii-lbl">FII / FPI Net</div><div class="fii-val">{fii_line}</div></div>
      <div class="fii-card"><div class="fii-lbl">DII Net</div><div class="fii-val">{dii_line}</div></div>
    </div>
    <h2 class="section-title">Full Agent Analysis</h2>
    <hr class="gold"/>
    <div class="cards-grid">
      {_card("Technical Analysis", "Market &amp; Price Action", market_report, signal_color, is_bullish)}
      {_card("Fundamental Analysis", "Financials &amp; Valuation", fundamentals_report)}
      {_card("News &amp; Macro", "India &amp; Global Coverage", news_report)}
      {_card("Social Sentiment", "Reddit &mdash; India Investing", supplementary.get('reddit_sentiment',''))}
      {_card("BSE Announcements", "Corporate Filings", supplementary.get('bse_announcements',''))}
      {_card("BSE Bulk Deals", "Institutional Trades", supplementary.get('bse_bulk_deals',''))}
      {_card("Bull Case", "Bullish Arguments", bull_history, "#16a34a")}
      {_card("Bear Case", "Bearish Arguments", bear_history, "#dc2626")}
      {_card("Risk Assessment", "Risk Debate", risk_judge, "#C9A24D")}
    </div>
    <h2 class="section-title">Final Recommendation</h2>
    <hr class="gold"/>
    <div class="final-card">
      <span class="eyebrow">Portfolio Manager Decision &middot; {trade_date}</span>
      <div class="card-title" style="font-size:17px;margin-bottom:8px">
        <span style="color:{signal_color}">{retail_label}</span>&nbsp;&middot;&nbsp;
        <span style="font-size:13px;color:{conf_color}">{conf_display} ({conf_label})</span>
      </div>
      <div class="card-body" style="margin-top:10px">{final_body}</div>
    </div>
  </div>

</div>

<div class="footer">
  Generated by Kodryx India Trading Agent &middot; {datetime.now().strftime("%d %b %Y %H:%M")} IST
  &middot; For research purposes only &middot; Not financial advice
</div>

{_MODE_JS}
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # ------------------------------------------------------------------
    # Persist to Layer 1 (DuckDB) + Layer 2 (Obsidian)
    # ------------------------------------------------------------------
    try:
        from tradingagents.dataflows.config import get_config
        cfg = get_config()

        # Layer 1 — signal + computed indicators
        db_path = cfg.get("db_path")
        if db_path:
            from tradingagents.storage.db import TradingDB
            with TradingDB(db_path) as db:
                db.write_signal(
                    ticker=ticker,
                    trade_date=trade_date,
                    signal=retail_label,
                    confidence=confidence_score,
                    tech_signal=tech_sig,
                    fund_signal=fund_sig,
                    macro_signal=macro_sig,
                    pm_signal=pm_sig,
                )
                db.write_indicators_bulk(ticker, trade_date, {
                    "rsi":    cs.get("rsi"),
                    "sma50":  cs.get("sma50"),
                    "sma200": cs.get("sma200"),
                    "ema10":  cs.get("ema10"),
                    "price":  cs.get("price"),
                })

        # Layer 2 — Obsidian vault notes
        vault_path = cfg.get("obsidian_vault_path")
        if vault_path:
            from tradingagents.storage.obsidian import ObsidianVault
            vault = ObsidianVault(vault_path)
            vault.write_stock_note(
                ticker=ticker,
                trade_date=trade_date,
                signal=retail_label,
                confidence=confidence_score,
                cs=cs,
                arbitration_narrative=arb_narrative,
            )
            vault.write_decision_note(
                ticker=ticker,
                trade_date=trade_date,
                signal=retail_label,
                confidence=confidence_score,
                arbitration_narrative=arb_narrative,
                final_body=final_decision,
                tech_signal=tech_sig or "",
                fund_signal=fund_sig or "",
                macro_signal=macro_sig or "",
                pm_signal=pm_sig,
            )
            if anomalies:
                for anomaly in anomalies:
                    vault.write_event_note(
                        ticker=ticker,
                        trade_date=trade_date,
                        anomaly_type="DATA_ANOMALY",
                        detail=anomaly,
                    )
    except Exception as _store_err:
        import logging as _log
        _log.getLogger(__name__).warning("Storage write skipped: %s", _store_err)

    return filepath
