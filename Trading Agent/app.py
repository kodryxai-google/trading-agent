"""Streamlit frontend — India Trading Agent  ·  Kodryx AI
Features (v2):
  · Full single-stock analysis with DeepSeek/Google
  · Trade CSV export (Zerodha/Kite compatible)
  · Basket analysis (portfolio cross-reference with FII/DII)
  · Backtest mode (date picker for historical runs)
  · Cache layer (reads pre-warmed Nifty 50 results)
  · Telegram delivery
"""
import csv
import io
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

REPORTS_DIR = Path(__file__).parent / "reports"
INDEX_PATH = REPORTS_DIR / "index.json"
CACHE_DIR  = REPORTS_DIR / "cache"

st.set_page_config(
    page_title="India Trading Agent · Kodryx AI",
    page_icon="\U0001f4c8",
    layout="wide",
)


# ═══════════════════════════════════════════════════════════════════════
#  Helpers — index & signal
# ═══════════════════════════════════════════════════════════════════════

def _parse_filename(filename: str) -> dict | None:
    m = re.match(r"(.+)_(\d{8})_(\d{6})\.html", filename)
    if not m:
        return None
    ticker, ds, ts = m.group(1), m.group(2), m.group(3)
    return {
        "ticker": ticker,
        "date": f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}",
        "time": f"{ts[:2]}:{ts[2:4]}:{ts[4:6]}",
        "datetime": f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}T{ts[:2]}:{ts[2:4]}:{ts[4:6]}",
        "filename": filename,
    }


def _extract_signal(html_path: Path) -> str:
    try:
        text = html_path.read_text(encoding="utf-8")
        m = re.search(r'Signal:\s*<span[^>]*>([^<]+)</span>', text)
        return m.group(1).strip() if m else "Unknown"
    except Exception:
        return "Unknown"


def _read_index() -> list[dict]:
    entries: list[dict] = []
    if INDEX_PATH.exists():
        try:
            entries = json.loads(INDEX_PATH.read_text())
        except json.JSONDecodeError:
            entries = []
    known = {e["filename"] for e in entries}
    for p in sorted(REPORTS_DIR.glob("*.html")):
        if p.name not in known:
            info = _parse_filename(p.name)
            if info:
                info["signal"] = _extract_signal(p)
                entries.append(info)
                known.add(p.name)
    entries.sort(key=lambda e: e.get("datetime", ""), reverse=True)
    _write_index(entries)
    return entries


def _write_index(entries: list[dict]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(entries, indent=2))


def _add_to_index(report_path: str, signal: str) -> None:
    info = _parse_filename(Path(report_path).name)
    if not info:
        return
    info["signal"] = signal
    entries = _read_index()
    entries = [e for e in entries if e["filename"] != info["filename"]]
    entries.append(info)
    entries.sort(key=lambda e: e.get("datetime", ""), reverse=True)
    _write_index(entries)


# ═══════════════════════════════════════════════════════════════════════
#  Pipeline helper
# ═══════════════════════════════════════════════════════════════════════

def _build_llm_config(results_dir: str) -> dict:
    from tradingagents.default_config import DEFAULT_CONFIG
    config = DEFAULT_CONFIG.copy()
    if os.environ.get("DEEPSEEK_API_KEY"):
        config["llm_provider"] = "deepseek"
        config["deep_think_llm"] = "deepseek-chat"
        config["quick_think_llm"] = "deepseek-chat"
    elif os.environ.get("GOOGLE_API_KEY"):
        config["llm_provider"] = "google"
        config["deep_think_llm"] = "gemini-2.5-flash"
        config["quick_think_llm"] = "gemini-2.5-flash"
    else:
        st.error("No LLM API key configured (DEEPSEEK_API_KEY / GOOGLE_API_KEY)")
        st.stop()
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1
    config["results_dir"] = results_dir
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "yfinance",
        "news_data": "india",
    }
    return config


def _run_pipeline(ticker_ns: str, trade_date: str, progress=None) -> dict[str, Any]:
    """Run the full multi-agent pipeline and return everything needed."""
    ticker_base = ticker_ns.replace(".NS", "").replace(".BO", "")

    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.dataflows.india_bse import (
        get_bse_announcements,
        get_bse_bulk_deals,
    )
    from tradingagents.dataflows.india_fii_dii import get_fii_dii_activity
    from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
    from tradingagents.dataflows.india_report import generate_report
    from tradingagents.utils.cache import write_cache

    config = _build_llm_config(str(REPORTS_DIR / ticker_base))
    ta = TradingAgentsGraph(debug=False, config=config)
    final_state, signal = ta.propagate(ticker_ns, trade_date, progress=progress)

    if progress:
        progress.emit_done("__supplementary__", snippet="Fetching BSE, FII/DII, Reddit data")

    look_back = "2026-04-01"
    supplementary = {
        "bse_announcements": get_bse_announcements(ticker_ns, look_back, trade_date),
        "bse_bulk_deals": get_bse_bulk_deals(ticker_ns),
        "fii_dii": get_fii_dii_activity(trade_date),
        "reddit_sentiment": get_india_reddit_sentiment(ticker_ns, look_back, trade_date),
    }

    if progress:
        progress.emit_done("__report__", snippet="Generating HTML report")

    report_path = generate_report(
        ticker=ticker_ns,
        trade_date=trade_date,
        final_state=final_state,
        signal=signal,
        supplementary=supplementary,
    )

    # CSV export
    from tradingagents.utils.csv_export import save_trade_csv
    decision = final_state.get("final_trade_decision", "")
    save_trade_csv(report_path, ticker_ns, signal, decision)

    # Cache
    write_cache(ticker_ns, trade_date, final_state, signal, supplementary)

    # Telegram
    from tradingagents.utils.telegram import send_report_summary
    market_report = final_state.get("market_report", "")
    send_report_summary(ticker_base, trade_date, signal, market_report, report_path)

    return {
        "report_path": report_path,
        "signal": signal,
        "final_state": final_state,
        "supplementary": supplementary,
    }


def _load_from_cache(ticker_ns: str, trade_date: str) -> dict[str, Any] | None:
    """Load cached analysis and regenerate HTML+CSV from cached state."""
    from tradingagents.utils.cache import read_cache
    cache = read_cache(ticker_ns, trade_date)
    if not cache:
        return None

    ticker_base = ticker_ns.replace(".NS", "").replace(".BO", "")
    from tradingagents.dataflows.india_report import generate_report

    report_path = generate_report(
        ticker=ticker_ns,
        trade_date=trade_date,
        final_state=cache["final_state"],
        signal=cache["signal"],
        supplementary=cache["supplementary"],
    )

    from tradingagents.utils.csv_export import save_trade_csv
    decision = cache["final_state"].get("final_trade_decision", "")
    save_trade_csv(report_path, ticker_ns, cache["signal"], decision)

    return {
        "report_path": report_path,
        "signal": cache["signal"],
        "final_state": cache["final_state"],
        "supplementary": cache["supplementary"],
        "from_cache": True,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Sidebar
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.markdown("## \U0001f4c2 History")
entries = _read_index()

if entries:
    labels = [
        f"{e['ticker']}  ·  {e['signal']}  ·  {e['date']} {e['time']}"
        for e in entries
    ]
    selected_label = st.sidebar.selectbox(
        "Previously analysed", labels, index=0, label_visibility="collapsed"
    )
    idx = labels.index(selected_label)
    st.session_state["selected_report"] = str(REPORTS_DIR / entries[idx]["filename"])
    st.session_state["selected_signal"] = entries[idx].get("signal", "Unknown")
else:
    st.sidebar.caption("No reports yet. Run your first analysis!")

st.sidebar.divider()

# ── Basket Analysis ──
st.sidebar.markdown("## \U0001f4e6 Basket Analysis")
basket_file = st.sidebar.file_uploader(
    "Upload portfolio CSV",
    type=["csv"],
    help="CSV with columns: symbol,quantity,buy_price",
)
if basket_file:
    content = basket_file.read().decode()
    today = date.today().isoformat()

    from tradingagents.utils.basket import analyse_basket
    rows, summary = analyse_basket(content, today)

    st.sidebar.metric("Stocks", summary["total_stocks"])
    fii = summary.get("fii_net")
    if fii is not None:
        st.sidebar.metric("FII Net", f"{fii:+,.0f} Cr")
    dii = summary.get("dii_net")
    if dii is not None:
        st.sidebar.metric("DII Net", f"{dii:+,.0f} Cr")

    df = pd.DataFrame(rows)
    st.sidebar.dataframe(
        df,
        column_config={
            "symbol": "Symbol",
            "price": st.column_config.NumberColumn("Price", format="₹%.2f"),
            "pe": st.column_config.NumberColumn("P/E", format="%.1f"),
            "sentiment": st.column_config.Column("FII Flow", width="small"),
        },
        hide_index=True,
        height=300,
    )

st.sidebar.divider()

# ── Cache status ──
st.sidebar.markdown("## \u23f3 Cache")
status_file = CACHE_DIR / "status.json"
if status_file.exists():
    try:
        s = json.loads(status_file.read_text())
        st.sidebar.caption(
            f"N50 pre-warm: {s.get('date', '?')}  ·  "
            f"{s.get('succeeded', 0)}/{s.get('total', 0)} ok"
        )
    except Exception:
        st.sidebar.caption("No pre-warm data")
else:
    st.sidebar.caption("Run scheduler.py overnight")

# ── Telegram status ──
st.sidebar.markdown("## \u2709 Telegram")
from tradingagents.utils.telegram import _is_configured
if _is_configured():
    st.sidebar.success("Connected")
else:
    st.sidebar.caption("Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env")


# ═══════════════════════════════════════════════════════════════════════
#  Main area
# ═══════════════════════════════════════════════════════════════════════

_, col_title, _ = st.columns([1, 3, 1])
with col_title:
    st.markdown(
        "<h1 style='text-align:center'>\U0001f4c8 India Trading Agent</h1>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Multi-agent LLM stock analysis · DeepSeek V4 Pro  |  "
        "CSV Export  ·  Basket  ·  Backtest  ·  Telegram"
    )

st.divider()

# ── Analysis form ──
col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
with col_a:
    ticker_in = st.text_input(
        "NSE Ticker",
        placeholder="e.g. TCS, RELIANCE, INFY",
        help="NSE symbol (.NS suffix added automatically)",
    )
with col_b:
    backtest_date = st.date_input(
        "Date",
        value=date.today(),
        help="Pick a past date for backtest analysis",
    )
with col_c:
    use_cache = st.checkbox("Cache", value=True, help="Use pre-warmed results if available")
with col_d:
    st.write("")
    run_btn = st.button(
        "\U0001f680  Analyse",
        type="primary",
        use_container_width=True,
        disabled=not ticker_in,
    )

if run_btn and ticker_in:
    ticker_base = ticker_in.upper().strip()
    ticker_ns = f"{ticker_base}.NS" if not ticker_base.endswith((".NS", ".BO")) else ticker_base
    trade_date = backtest_date.isoformat()

    result = None

    # Try cache first
    if use_cache and trade_date == date.today().isoformat():
        cached = _load_from_cache(ticker_ns, trade_date)
        if cached:
            st.info("⏳ Loaded from cache — instant")
            result = cached

    if result is None:
        import threading
        import time as _time
        from tradingagents.utils.progress import ProgressEmitter

        emitter = ProgressEmitter()
        result_box: dict = {}
        error_box: dict = {}

        def _worker():
            try:
                result_box["data"] = _run_pipeline(ticker_ns, trade_date, progress=emitter)
            except Exception as exc:
                error_box["err"] = str(exc)
                emitter.emit_error("__pipeline__", str(exc))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        PIPELINE_STEPS = [
            ("market_analyst",       "📊", "Market Analyst",        "#3B82F6"),
            ("social_media_analyst", "💬", "Social Analyst",        "#8B5CF6"),
            ("news_analyst",         "📰", "News Analyst",          "#06B6D4"),
            ("fundamentals_analyst", "🏦", "Fundamentals Analyst",  "#10B981"),
            ("bull_researcher",      "🐂", "Bull Researcher",       "#16A34A"),
            ("bear_researcher",      "🐻", "Bear Researcher",       "#DC2626"),
            ("research_manager",     "🧠", "Research Manager",      "#F59E0B"),
            ("trader",               "💼", "Trader",                "#6366F1"),
            ("risky_analyst",        "⚡",     "Risk — Aggressive","#EF4444"),
            ("safe_analyst",         "🛡", "Risk — Conservative","#22C55E"),
            ("neutral_analyst",      "⚖",     "Risk — Neutral",   "#94A3B8"),
            ("risk_manager",         "🎯", "Risk Manager",          "#F97316"),
            ("portfolio_manager",    "👔", "Portfolio Manager",     "#C9A24D"),
            ("__supplementary__",    "🌐", "Market Data Fetch",     "#0EA5E9"),
            ("__report__",           "📄", "Report Generation",     "#A855F7"),
        ]
        STEP_NODES = [s[0] for s in PIPELINE_STEPS]
        done_steps: dict = {}
        active_node = [STEP_NODES[0]]

        progress_container = st.empty()

        def _render(final: bool = False) -> str:
            completed = len(done_steps)
            total = len(PIPELINE_STEPS)
            pct = int(completed / total * 100)
            cards = ""
            for node, icon, label, color in PIPELINE_STEPS:
                if node in done_steps:
                    e = done_steps[node]
                    cards += f'''
<div class="sc done">
  <span class="si">{icon}</span>
  <span class="sl">{label}</span>
  <span class="st done-t">{e:.1f}s ✓</span>
</div>'''
                elif node == active_node[0] and not final:
                    cards += f'''
<div class="sc active" style="border-left-color:{color};box-shadow:0 0 0 1px {color}33">
  <span class="si spin">{icon}</span>
  <span class="sl" style="color:{color}">{label}</span>
  <span class="st pulse-t">Running…</span>
</div>'''
                else:
                    cards += f'''
<div class="sc pending">
  <span class="si dim">{icon}</span>
  <span class="sl dim">{label}</span>
  <span class="st dim">—</span>
</div>'''
            done_html = "<div class='done-msg'>✅ Analysis Complete!</div>" if final else ""
            return f"""
<style>
.dash{{font-family:'Segoe UI',sans-serif;background:#0F172A;border-radius:16px;padding:24px 28px 20px;color:#F1F5F9;max-width:680px}}
.dh{{display:flex;align-items:center;gap:12px;margin-bottom:18px}}
.dt{{font-size:16px;font-weight:600}}
.dtick{{background:#1E293B;border:1px solid #334155;border-radius:8px;padding:3px 10px;font-size:13px;color:#94A3B8;font-weight:500}}
.pb-wrap{{background:#1E293B;border-radius:99px;height:8px;margin-bottom:6px;overflow:hidden}}
.pb-fill{{height:100%;border-radius:99px;background:linear-gradient(90deg,#3B82F6,#C9A24D);width:{pct}%;transition:width .4s ease}}
.prog-lbl{{font-size:12px;color:#64748B;margin-bottom:18px}}
.steps{{display:flex;flex-direction:column;gap:6px}}
.sc{{display:flex;align-items:center;gap:10px;padding:9px 14px;border-radius:10px;border-left:3px solid transparent;background:#1E293B}}
.sc.done{{background:#0F2318;border-left-color:#22C55E;opacity:.9}}
.sc.pending{{opacity:.35}}
.si{{font-size:15px;width:20px;text-align:center;flex-shrink:0}}
.si.dim{{opacity:.4}}
.sl{{flex:1;font-size:13px;font-weight:500;color:#CBD5E1}}
.sl.dim{{color:#475569}}
.st{{font-size:11px;color:#64748B;min-width:60px;text-align:right}}
.st.dim{{color:#334155}}
.done-t{{color:#22C55E}}
.pulse-t{{color:#60A5FA;animation:fp 1.4s infinite}}
@keyframes fp{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
.spin{{display:inline-block;animation:ri 1.2s linear infinite}}
@keyframes ri{{from{{transform:rotate(0deg)}}to{{transform:rotate(360deg)}}}}
.done-msg{{margin-top:16px;text-align:center;font-size:15px;color:#22C55E;font-weight:600;letter-spacing:.5px}}
</style>
<div class="dash">
  <div class="dh">
    <span style="font-size:22px">🤖</span>
    <div class="dt">Kodryx AI — Multi-Agent Analysis</div>
    <div class="dtick">{ticker_base}</div>
  </div>
  <div class="pb-wrap"><div class="pb-fill"></div></div>
  <div class="prog-lbl">{completed} of {total} steps complete · {pct}%</div>
  <div class="steps">{cards}</div>
  {done_html}
</div>"""

        while t.is_alive() or not emitter._q.empty():
            for ev in emitter.drain():
                if ev.status == "done":
                    done_steps[ev.node] = ev.elapsed
                    for n in STEP_NODES:
                        if n not in done_steps:
                            active_node[0] = n
                            break
            progress_container.markdown(_render(), unsafe_allow_html=True)
            _time.sleep(0.5)

        progress_container.markdown(_render(final=True), unsafe_allow_html=True)
        _time.sleep(1.5)
        progress_container.empty()

        if "err" in error_box:
            st.error(f"Pipeline error: {error_box['err']}")
            st.stop()

        result = result_box["data"]
        if not result.get("from_cache"):
            st.toast("Telegram notification sent" if _is_configured() else "")

    _add_to_index(result["report_path"], result["signal"])
    st.session_state["selected_report"] = result["report_path"]
    st.session_state["selected_signal"] = result["signal"]
    st.session_state["report_result"] = result

    st.success(f"**{ticker_base}**  ·  Signal: **{result['signal']}**"
               f"{'  ·  (backtest)' if trade_date != date.today().isoformat() else ''}")
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  Report viewer
# ═══════════════════════════════════════════════════════════════════════

report_path = st.session_state.get("selected_report")
if report_path and Path(report_path).exists():
    signal = st.session_state.get("selected_signal", "")
    if signal:
        su = signal.upper()
        if "BUY" in su:
            colour = "#16a34a"
        elif "SELL" in su:
            colour = "#dc2626"
        else:
            colour = "#C9A24D"
        st.markdown(f"### Signal  ·  :{colour.replace('#', '')}[{signal}]")

    # ── Trade CSV download ──
    csv_path = Path(report_path).with_suffix(".csv")
    if csv_path.exists():
        col_r1, col_r2 = st.columns([1, 5])
        with col_r1:
            st.download_button(
                "\U0001f4e5 Trade CSV",
                data=csv_path.read_text(),
                file_name=csv_path.name,
                mime="text/csv",
                help="Import into Zerodha Kite, ICICI Direct, or Angel One basket order",
                use_container_width=True,
            )
        with col_r2:
            st.caption("Zerodha Kite → Basket → Import CSV  |  ICICI Direct → Basket → Upload")

    # ── HTML report ──
    html = Path(report_path).read_text(encoding="utf-8")
    st.components.v1.html(html, height=900, scrolling=True)
