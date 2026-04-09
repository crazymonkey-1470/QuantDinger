"""Financial news and economic calendar data providers."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_financial_news(lang: str = "all") -> Dict[str, List[Dict[str, Any]]]:
    """Fetch financial news using search service — separated by language."""
    result: Dict[str, List[Dict[str, Any]]] = {"cn": [], "en": []}

    try:
        from app.services.search import SearchService
        search = SearchService()

        cn_queries = [
            "加密货币新闻", "美联储利率", "美股市场最新消息",
            "外汇市场分析", "全球经济数据", "期货市场动态",
        ]
        en_queries = [
            "stock market news today", "cryptocurrency bitcoin news",
            "forex market analysis", "federal reserve interest rate",
            "global economic outlook", "S&P 500 market update",
        ]

        if lang in ("all", "cn"):
            for query in cn_queries:
                try:
                    results = search.search(query, num_results=5, date_restrict="d1")
                    for r in results:
                        result["cn"].append({
                            "title": r.get("title", ""), "link": r.get("link", ""),
                            "snippet": r.get("snippet", ""), "source": r.get("source", ""),
                            "published": r.get("published", ""), "category": query, "lang": "cn",
                        })
                except Exception:
                    pass

        if lang in ("all", "en"):
            for query in en_queries:
                try:
                    results = search.search(query, num_results=5, date_restrict="d1")
                    for r in results:
                        result["en"].append({
                            "title": r.get("title", ""), "link": r.get("link", ""),
                            "snippet": r.get("snippet", ""), "source": r.get("source", ""),
                            "published": r.get("published", ""), "category": query, "lang": "en",
                        })
                except Exception:
                    pass

        for lang_key in ["cn", "en"]:
            seen: set = set()
            unique = []
            for news in result[lang_key]:
                link = news.get("link", "")
                if link and link not in seen:
                    seen.add(link)
                    unique.append(news)
            result[lang_key] = unique[:15]

    except Exception as e:
        logger.error("Failed to fetch financial news: %s", e)

    return result


# ---------------------------------------------------------------------------
# Economic calendar (template-based, no real API yet)
# ---------------------------------------------------------------------------

_SAMPLE_EVENTS = [
    {"name": "美国非农就业数据", "name_en": "US Non-Farm Payrolls", "country": "US", "importance": "high", "forecast": "180K", "previous": "175K", "impact_if_above": "bullish", "impact_if_below": "bearish", "impact_desc": "高于预期利多美元/美股，低于预期利空", "impact_desc_en": "Above forecast: bullish USD/stocks; Below: bearish"},
    {"name": "美联储利率决议", "name_en": "Fed Interest Rate Decision", "country": "US", "importance": "high", "forecast": "5.25%", "previous": "5.25%", "impact_if_above": "bearish", "impact_if_below": "bullish", "impact_desc": "加息利空股市/加密货币，降息利多", "impact_desc_en": "Rate hike: bearish stocks/crypto; Cut: bullish"},
    {"name": "美国CPI月率", "name_en": "US CPI m/m", "country": "US", "importance": "high", "forecast": "0.3%", "previous": "0.4%", "impact_if_above": "bearish", "impact_if_below": "bullish", "impact_desc": "CPI高于预期增加加息预期，利空股市", "impact_desc_en": "Higher CPI increases rate hike expectations, bearish stocks"},
    {"name": "欧洲央行利率决议", "name_en": "ECB Interest Rate Decision", "country": "EU", "importance": "high", "forecast": "4.50%", "previous": "4.50%", "impact_if_above": "bearish", "impact_if_below": "bullish", "impact_desc": "加息利空欧股，利多欧元", "impact_desc_en": "Rate hike: bearish EU stocks, bullish EUR"},
    {"name": "日本央行利率决议", "name_en": "BoJ Interest Rate Decision", "country": "JP", "importance": "high", "forecast": "0.10%", "previous": "0.10%", "impact_if_above": "bullish", "impact_if_below": "bearish", "impact_desc": "加息预期利多日元，利空日股", "impact_desc_en": "Rate hike expectation: bullish JPY, bearish Nikkei"},
    {"name": "美国初请失业金人数", "name_en": "US Initial Jobless Claims", "country": "US", "importance": "medium", "forecast": "215K", "previous": "212K", "impact_if_above": "bearish", "impact_if_below": "bullish", "impact_desc": "失业人数上升利空美元，利多黄金", "impact_desc_en": "Rising claims: bearish USD, bullish gold"},
    {"name": "英国央行利率决议", "name_en": "BoE Interest Rate Decision", "country": "UK", "importance": "high", "forecast": "5.25%", "previous": "5.25%", "impact_if_above": "bullish", "impact_if_below": "bearish", "impact_desc": "加息利多英镑，利空英股", "impact_desc_en": "Rate hike: bullish GBP, bearish UK stocks"},
    {"name": "美国零售销售月率", "name_en": "US Retail Sales m/m", "country": "US", "importance": "medium", "forecast": "0.4%", "previous": "0.6%", "impact_if_above": "bullish", "impact_if_below": "bearish", "impact_desc": "零售数据强劲利多美元和美股", "impact_desc_en": "Strong retail: bullish USD and stocks"},
    {"name": "OPEC月度报告", "name_en": "OPEC Monthly Report", "country": "INTL", "importance": "medium", "forecast": "-", "previous": "-", "impact_if_above": "bullish", "impact_if_below": "bearish", "impact_desc": "减产预期利多原油，增产预期利空", "impact_desc_en": "Production cut: bullish oil; Increase: bearish"},
]


def get_economic_calendar() -> List[Dict[str, Any]]:
    """Generate economic calendar events with impact indicators."""
    today = datetime.now()
    events = []

    for i, evt in enumerate(_SAMPLE_EVENTS):
        days_offset = i % 14 - 5
        event_date = today + timedelta(days=days_offset)
        hour = (8 + (i * 3)) % 24

        is_released = event_date.date() < today.date() or (
            event_date.date() == today.date() and hour < today.hour
        )

        actual_value = None
        actual_impact = None
        expected_impact = evt["impact_if_above"]

        if is_released:
            forecast_num = "".join(filter(lambda x: x.isdigit() or x == ".", evt["forecast"]))
            if forecast_num:
                try:
                    base = float(forecast_num)
                    variation = random.uniform(-0.15, 0.15)
                    actual_num = base * (1 + variation)
                    if "K" in evt["forecast"]:
                        actual_value = f"{actual_num:.0f}K"
                    elif "%" in evt["forecast"]:
                        actual_value = f"{actual_num:.2f}%"
                    else:
                        actual_value = f"{actual_num:.2f}"
                    if actual_num > base:
                        actual_impact = evt["impact_if_above"]
                    elif actual_num < base:
                        actual_impact = evt["impact_if_below"]
                    else:
                        actual_impact = "neutral"
                except Exception:
                    actual_value = evt["forecast"]
                    actual_impact = "neutral"
            else:
                actual_value = evt["forecast"]
                actual_impact = "neutral"

        events.append({
            "id": i + 1,
            "name": evt["name"], "name_en": evt["name_en"],
            "country": evt["country"],
            "date": event_date.strftime("%Y-%m-%d"),
            "time": f"{hour:02d}:30",
            "importance": evt["importance"],
            "actual": actual_value, "forecast": evt["forecast"], "previous": evt["previous"],
            "impact_if_above": evt["impact_if_above"], "impact_if_below": evt["impact_if_below"],
            "impact_desc": evt["impact_desc"], "impact_desc_en": evt["impact_desc_en"],
            "expected_impact": expected_impact, "actual_impact": actual_impact,
            "is_released": is_released,
        })

    events.sort(key=lambda x: (x["date"], x["time"]))
    return events
