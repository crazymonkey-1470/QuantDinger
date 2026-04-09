"""
Global Market Dashboard APIs.

Provides aggregated global market data including:
- Major indices (US, Europe, Japan, Korea, Australia, India)
- Forex pairs
- Crypto prices
- Market heatmap data (crypto, stocks, forex)
- Economic calendar with impact indicators
- Fear & Greed Index / VIX
- Financial news (Chinese & English)

Endpoints:
- GET /api/global-market/overview       - Global market overview
- GET /api/global-market/heatmap        - Market heatmap data
- GET /api/global-market/news           - Financial news (with lang param)
- GET /api/global-market/calendar       - Economic calendar
- GET /api/global-market/sentiment      - Fear & Greed / VIX
- GET /api/global-market/opportunities  - Trading opportunities scanner
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Blueprint, jsonify, request

from app.utils.logger import get_logger
from app.utils.auth import login_required

# Unified data-provider layer
from app.data_providers import get_cached, set_cached, clear_cache
from app.data_providers.crypto import fetch_crypto_prices
from app.data_providers.forex import fetch_forex_pairs
from app.data_providers.commodities import fetch_commodities
from app.data_providers.indices import fetch_stock_indices
from app.data_providers.sentiment import (
    fetch_fear_greed_index, fetch_vix, fetch_dollar_index,
    fetch_yield_curve, fetch_vxn, fetch_gvz, fetch_put_call_ratio,
)
from app.data_providers.news import fetch_financial_news, get_economic_calendar
from app.data_providers.heatmap import generate_heatmap_data
from app.data_providers.opportunities import (
    analyze_opportunities_crypto, analyze_opportunities_stocks,
    analyze_opportunities_local_stocks, analyze_opportunities_forex,
)

logger = get_logger(__name__)

global_market_bp = Blueprint("global_market", __name__)


# ============ API Endpoints ============

@global_market_bp.route("/overview", methods=["GET"])
@login_required
def market_overview():
    """Get global market overview including indices, forex, crypto, and commodities."""
    try:
        cached = get_cached("market_overview", 30)
        if cached:
            logger.debug(
                "Returning cached overview: indices=%d, forex=%d, crypto=%d, commodities=%d",
                len(cached.get("indices", [])), len(cached.get("forex", [])),
                len(cached.get("crypto", [])), len(cached.get("commodities", [])),
            )
            return jsonify({"code": 1, "msg": "success", "data": cached})

        logger.info("Fetching fresh market overview data...")

        result = {
            "indices": [], "forex": [], "crypto": [], "commodities": [],
            "timestamp": int(time.time()),
        }

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(fetch_stock_indices): "indices",
                executor.submit(fetch_forex_pairs): "forex",
                executor.submit(fetch_crypto_prices): "crypto",
                executor.submit(fetch_commodities): "commodities",
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    data = future.result()
                    result[key] = data if data else []
                    logger.info("Fetched %s: %d items", key, len(result[key]))
                    set_cached(f"{key}_data", result[key], 30)
                except Exception as e:
                    logger.error("Failed to fetch %s: %s", key, e, exc_info=True)
                    result[key] = []

        logger.info(
            "Market overview complete: indices=%d, forex=%d, crypto=%d, commodities=%d",
            len(result["indices"]), len(result["forex"]),
            len(result["crypto"]), len(result["commodities"]),
        )

        set_cached("stock_indices", result["indices"], 30)
        set_cached("forex_pairs", result["forex"], 30)
        set_cached("crypto_prices", result["crypto"], 30)
        set_cached("market_overview", result, 30)

        return jsonify({"code": 1, "msg": "success", "data": result})

    except Exception as e:
        logger.error("market_overview failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@global_market_bp.route("/heatmap", methods=["GET"])
@login_required
def market_heatmap():
    """Get market heatmap data for crypto, stock sectors, forex, and indices."""
    try:
        cached = get_cached("market_heatmap", 30)
        if cached:
            return jsonify({"code": 1, "msg": "success", "data": cached})

        data = generate_heatmap_data()
        set_cached("market_heatmap", data, 30)

        return jsonify({"code": 1, "msg": "success", "data": data})

    except Exception as e:
        logger.error("market_heatmap failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@global_market_bp.route("/news", methods=["GET"])
@login_required
def market_news():
    """Get financial news from various sources.  Query params: lang ('cn'|'en'|'all')."""
    try:
        lang = request.args.get("lang", "all")
        cache_key = f"market_news_{lang}"

        cached = get_cached(cache_key, 180)
        if cached:
            return jsonify({"code": 1, "msg": "success", "data": cached})

        news = fetch_financial_news(lang)
        set_cached(cache_key, news, 180)

        return jsonify({"code": 1, "msg": "success", "data": news})

    except Exception as e:
        logger.error("market_news failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@global_market_bp.route("/calendar", methods=["GET"])
@login_required
def economic_calendar():
    """Get economic calendar events with impact indicators."""
    try:
        cached = get_cached("economic_calendar", 3600)
        if cached:
            return jsonify({"code": 1, "msg": "success", "data": cached})

        events = get_economic_calendar()
        set_cached("economic_calendar", events, 3600)

        return jsonify({"code": 1, "msg": "success", "data": events})

    except Exception as e:
        logger.error("economic_calendar failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@global_market_bp.route("/sentiment", methods=["GET"])
@login_required
def market_sentiment():
    """Get comprehensive market sentiment indicators."""
    try:
        MACRO_CACHE_TTL = 21600
        cached = get_cached("market_sentiment", MACRO_CACHE_TTL)
        if cached:
            logger.debug("Returning cached sentiment data (6h cache)")
            return jsonify({"code": 1, "msg": "success", "data": cached})

        logger.info("Fetching fresh sentiment data (comprehensive)")

        with ThreadPoolExecutor(max_workers=7) as executor:
            futures = {
                executor.submit(fetch_fear_greed_index): "fear_greed",
                executor.submit(fetch_vix): "vix",
                executor.submit(fetch_dollar_index): "dxy",
                executor.submit(fetch_yield_curve): "yield_curve",
                executor.submit(fetch_vxn): "vxn",
                executor.submit(fetch_gvz): "gvz",
                executor.submit(fetch_put_call_ratio): "vix_term",
            }
            results = {}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    logger.error("Failed to fetch %s: %s", key, e)
                    results[key] = None

        logger.info(
            "Sentiment data fetched: Fear&Greed=%s, VIX=%s, DXY=%s",
            results.get("fear_greed", {}).get("value"),
            results.get("vix", {}).get("value"),
            results.get("dxy", {}).get("value"),
        )

        data = {
            "fear_greed": results.get("fear_greed") or {"value": 50, "classification": "Neutral"},
            "vix": results.get("vix") or {"value": 0, "level": "unknown"},
            "dxy": results.get("dxy") or {"value": 0, "level": "unknown"},
            "yield_curve": results.get("yield_curve") or {"spread": 0, "level": "unknown"},
            "vxn": results.get("vxn") or {"value": 0, "level": "unknown"},
            "gvz": results.get("gvz") or {"value": 0, "level": "unknown"},
            "vix_term": results.get("vix_term") or {"value": 1.0, "level": "unknown"},
            "timestamp": int(time.time()),
        }

        set_cached("market_sentiment", data, MACRO_CACHE_TTL)

        return jsonify({"code": 1, "msg": "success", "data": data})

    except Exception as e:
        logger.error("market_sentiment failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@global_market_bp.route("/opportunities", methods=["GET"])
@login_required
def trading_opportunities():
    """Scan for trading opportunities across Crypto, US/CN/HK Stocks, and Forex."""
    try:
        force = request.args.get("force", "").lower() in ("true", "1")

        if not force:
            cached = get_cached("trading_opportunities")
            if cached:
                return jsonify({"code": 1, "msg": "success", "data": cached})

        opportunities: list = []

        scanners = [
            ("Crypto", lambda: analyze_opportunities_crypto(opportunities)),
            ("USStock", lambda: analyze_opportunities_stocks(opportunities)),
            ("CNStock", lambda: analyze_opportunities_local_stocks(opportunities, "CNStock")),
            ("HKStock", lambda: analyze_opportunities_local_stocks(opportunities, "HKStock")),
            ("Forex", lambda: analyze_opportunities_forex(opportunities)),
        ]
        for label, scanner in scanners:
            try:
                scanner()
                count = len([o for o in opportunities if o.get("market") == label])
                logger.info("Trading opportunities: found %d %s opportunities", count, label)
            except Exception as e:
                logger.error("Failed to analyze %s opportunities: %s", label, e, exc_info=True)

        opportunities.sort(key=lambda x: abs(x.get("change_24h", 0)), reverse=True)

        by_market = {}
        for o in opportunities:
            by_market[o.get("market", "?")] = by_market.get(o.get("market", "?"), 0) + 1
        logger.info("Trading opportunities: total %d (%s)", len(opportunities), by_market)

        set_cached("trading_opportunities", opportunities, 3600)

        return jsonify({"code": 1, "msg": "success", "data": opportunities})

    except Exception as e:
        logger.error("trading_opportunities failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500


@global_market_bp.route("/refresh", methods=["POST"])
@login_required
def refresh_data():
    """Force refresh all market data (clears cache)."""
    try:
        clear_cache()
        return jsonify({"code": 1, "msg": "Cache cleared successfully", "data": None})
    except Exception as e:
        logger.error("refresh_data failed: %s", e, exc_info=True)
        return jsonify({"code": 0, "msg": str(e), "data": None}), 500
