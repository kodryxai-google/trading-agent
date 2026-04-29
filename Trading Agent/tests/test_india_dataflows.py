"""Tests for India-specific dataflow modules."""
import pytest
from unittest.mock import patch, MagicMock


class TestIndiaNews:
    def test_returns_string(self):
        from tradingagents.dataflows.india_news import get_india_stock_news
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
            mock_resp.raise_for_status = MagicMock()
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
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            result = get_india_macro_news("2026-04-29", look_back_days=7)
        assert isinstance(result, str)


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
        assert len(result) > 0

    def test_handles_empty_response(self):
        from tradingagents.dataflows.india_reddit import get_india_reddit_sentiment
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"children": []}}
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = get_india_reddit_sentiment("TCS.NS", "2026-04-22", "2026-04-29")
        assert isinstance(result, str)


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
            mock_resp.raise_for_status = MagicMock()
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
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp
            result = get_bse_bulk_deals("TCS.NS")
        assert isinstance(result, str)


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
            mock_session.get.return_value.raise_for_status = MagicMock()
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


class TestIndiaVendorRouting:
    def test_india_vendor_registered_for_news(self):
        from tradingagents.dataflows.interface import VENDOR_METHODS
        assert "india" in VENDOR_METHODS["get_news"]
        assert "india" in VENDOR_METHODS["get_global_news"]

    def test_india_vendor_callable(self):
        from tradingagents.dataflows.interface import VENDOR_METHODS
        fn = VENDOR_METHODS["get_news"]["india"]
        assert callable(fn)
