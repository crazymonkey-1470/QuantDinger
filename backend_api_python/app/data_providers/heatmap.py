"""Heatmap data aggregator — pulls from crypto / forex / commodities / indices."""
from __future__ import annotations

import math
from typing import Any, Dict

from app.utils.logger import get_logger
from app.data_providers import get_cached, set_cached, safe_float
from app.data_providers.crypto import (
    fetch_crypto_heatmap_coingecko,
    fetch_crypto_heatmap_coincap,
    fetch_crypto_prices,
)
from app.data_providers.forex import fetch_forex_pairs
from app.data_providers.commodities import fetch_commodities

logger = get_logger(__name__)


def generate_heatmap_data() -> Dict[str, Any]:
    """Generate heatmap data for crypto, stock sectors, forex, commodities, and indices."""

    # ---- Crypto ----
    crypto_data = get_cached("crypto_heatmap")
    if not crypto_data:
        for fetcher in (fetch_crypto_heatmap_coingecko, fetch_crypto_heatmap_coincap, fetch_crypto_prices):
            try:
                crypto_data = fetcher()
                if crypto_data and len(crypto_data) >= 5:
                    set_cached("crypto_heatmap", crypto_data, 300)
                    break
            except Exception as e:
                logger.debug("Crypto heatmap fetcher %s failed: %s", fetcher.__name__, e)
        if not crypto_data:
            crypto_data = get_cached("crypto_prices") or []

    # ---- Forex ----
    forex_data = get_cached("forex_pairs")
    if not forex_data:
        forex_data = fetch_forex_pairs()
        set_cached("forex_pairs", forex_data, 30)

    heatmap: Dict[str, Any] = {
        "crypto": [],
        "sectors": [],
        "forex": [],
        "commodities": [],
        "indices": [],
    }

    # Commodities
    commodities_data = get_cached("commodities")
    if not commodities_data:
        commodities_data = fetch_commodities()
        set_cached("commodities", commodities_data)

    for comm in (commodities_data or []):
        heatmap["commodities"].append({
            "name": comm.get("name_cn", comm.get("name_en", "")),
            "name_cn": comm.get("name_cn", ""),
            "name_en": comm.get("name_en", ""),
            "value": comm.get("change", 0),
            "price": comm.get("price", 0),
            "unit": comm.get("unit", ""),
        })

    # Crypto — sort by market cap, top 25
    crypto_sorted = sorted(
        (crypto_data or []),
        key=lambda x: safe_float(x.get("market_cap", 0)),
        reverse=True,
    )
    for coin in [c for c in crypto_sorted if c.get("symbol")][:25]:
        heatmap["crypto"].append({
            "name": coin.get("symbol", ""),
            "fullName": coin.get("name", ""),
            "value": coin.get("change_24h", 0),
            "marketCap": coin.get("market_cap", 0),
            "volume": coin.get("volume_24h", 0),
            "price": coin.get("price", 0),
        })

    # Forex
    for pair in forex_data:
        heatmap["forex"].append({
            "name": pair.get("name", ""),
            "name_cn": pair.get("name_cn", pair.get("name", "")),
            "name_en": pair.get("name_en", pair.get("name", "")),
            "value": pair.get("change", 0),
            "price": pair.get("price", 0),
        })

    # Sectors (via ETFs)
    sectors = [
        {"name": "科技", "name_en": "Technology", "etf": "XLK", "value": 0, "stocks": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"]},
        {"name": "金融", "name_en": "Financials", "etf": "XLF", "value": 0, "stocks": ["JPM", "BAC", "WFC", "GS", "MS"]},
        {"name": "医疗", "name_en": "Healthcare", "etf": "XLV", "value": 0, "stocks": ["JNJ", "PFE", "UNH", "MRK", "ABBV"]},
        {"name": "消费", "name_en": "Consumer", "etf": "XLY", "value": 0, "stocks": ["AMZN", "TSLA", "HD", "NKE", "MCD"]},
        {"name": "能源", "name_en": "Energy", "etf": "XLE", "value": 0, "stocks": ["XOM", "CVX", "COP", "SLB", "EOG"]},
        {"name": "工业", "name_en": "Industrials", "etf": "XLI", "value": 0, "stocks": ["CAT", "BA", "GE", "HON", "UPS"]},
        {"name": "材料", "name_en": "Materials", "etf": "XLB", "value": 0, "stocks": ["LIN", "APD", "DD", "NEM", "FCX"]},
        {"name": "公用事业", "name_en": "Utilities", "etf": "XLU", "value": 0, "stocks": ["NEE", "DUK", "SO", "D", "AEP"]},
        {"name": "房地产", "name_en": "Real Estate", "etf": "XLRE", "value": 0, "stocks": ["AMT", "PLD", "CCI", "EQIX", "SPG"]},
        {"name": "通信", "name_en": "Communication", "etf": "XLC", "value": 0, "stocks": ["GOOGL", "META", "DIS", "NFLX", "VZ"]},
    ]

    try:
        import yfinance as yf
        etf_symbols = [s["etf"] for s in sectors]
        tickers = yf.Tickers(" ".join(etf_symbols))

        for sector in sectors:
            try:
                ticker = tickers.tickers.get(sector["etf"])
                if ticker:
                    hist = ticker.history(period="2d")
                    if len(hist) >= 2:
                        prev = float(hist["Close"].iloc[-2])
                        curr = float(hist["Close"].iloc[-1])
                        if not (math.isnan(prev) or math.isnan(curr)) and prev > 0:
                            sector["value"] = round(((curr - prev) / prev) * 100, 2)
                    elif len(hist) == 1:
                        sector["value"] = 0
            except Exception:
                pass
    except Exception as e:
        logger.debug("Failed to fetch sector ETFs: %s", e)

    heatmap["sectors"] = sectors

    # Indices (piggyback on overview cache)
    indices_data = get_cached("stock_indices")
    if indices_data:
        for idx in indices_data:
            heatmap["indices"].append({
                "symbol": idx.get("symbol", ""),
                "name": idx.get("name_cn", idx.get("name", "")),
                "name_cn": idx.get("name_cn", ""),
                "name_en": idx.get("name_en", ""),
                "region": idx.get("region", ""),
                "value": idx.get("change", 0),
                "price": idx.get("price", 0),
                "flag": idx.get("flag", ""),
            })

    return heatmap
