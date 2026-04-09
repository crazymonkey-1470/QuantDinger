"""
Heuristic quality hints for QuantDinger indicator Python code.

Read-only analysis: @strategy parsing, structure checks, risk/position sanity.
Does not execute user code.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.indicator_params import StrategyConfigParser

# 历史代码里可能出现 @strategy leverage；已由回测面板接管，不计入「未知键」告警
_IGNORED_STRATEGY_KEYS = frozenset({"leverage"})


def _has_df_buy_sell(code: str) -> bool:
    c = code or ""
    if re.search(r"df\s*\[\s*['\"]buy['\"]\s*\]", c):
        return True
    if re.search(r"df\s*\[\s*['\"]sell['\"]\s*\]", c):
        return True
    return False


def _has_output_dict(code: str) -> bool:
    if re.search(r"\boutput\s*=\s*\{", code or ""):
        return True
    return False


def _has_my_indicator_meta(code: str) -> tuple[bool, bool]:
    c = code or ""
    name = bool(re.search(r"^\s*my_indicator_name\s*=", c, re.MULTILINE))
    desc = bool(re.search(r"^\s*my_indicator_description\s*=", c, re.MULTILINE))
    return name, desc


def _has_df_copy(code: str) -> bool:
    return bool(re.search(r"df\s*=\s*df\.copy\s*\(\s*\)", code or ""))


def _unknown_strategy_keys(code: str) -> List[str]:
    valid = set(StrategyConfigParser.VALID_KEYS.keys())
    unknown: List[str] = []
    for m in re.finditer(
        r"^\s*#\s*@strategy\s+(\w+)\s+(\S+)", code or "", re.MULTILINE | re.IGNORECASE
    ):
        key = m.group(1)
        if key not in valid:
            if key in _IGNORED_STRATEGY_KEYS:
                continue
            unknown.append(key)
    return unknown


def analyze_indicator_code_quality(code: str) -> List[Dict[str, Any]]:
    """
    Returns a list of hints:
      { "severity": "info"|"warn"|"error", "code": str, "params": dict optional }
    """
    hints: List[Dict[str, Any]] = []
    raw = (code or "").strip()
    if not raw:
        return [{"severity": "error", "code": "EMPTY_CODE", "params": {}}]

    name_ok, desc_ok = _has_my_indicator_meta(raw)
    if not name_ok:
        hints.append({"severity": "warn", "code": "MISSING_INDICATOR_NAME", "params": {}})
    if not desc_ok:
        hints.append({"severity": "info", "code": "MISSING_INDICATOR_DESCRIPTION", "params": {}})

    if not _has_df_copy(raw):
        hints.append({"severity": "info", "code": "MISSING_DF_COPY", "params": {}})

    if not _has_output_dict(raw):
        hints.append({"severity": "error", "code": "MISSING_OUTPUT", "params": {}})

    trading = _has_df_buy_sell(raw)
    if not trading:
        hints.append({"severity": "warn", "code": "MISSING_BUY_SELL_COLUMNS", "params": {}})

    for bad_key in _unknown_strategy_keys(raw):
        hints.append(
            {
                "severity": "warn",
                "code": "UNKNOWN_STRATEGY_KEY",
                "params": {"key": bad_key},
            }
        )

    cfg = StrategyConfigParser.parse(raw)

    if trading:
        if not cfg:
            hints.append(
                {
                    "severity": "info",
                    "code": "NO_STRATEGY_ANNOTATIONS",
                    "params": {},
                }
            )
        else:
            slp = cfg.get("stopLossPct")
            tpp = cfg.get("takeProfitPct")
            if slp is None and tpp is None:
                hints.append(
                    {
                        "severity": "warn",
                        "code": "NO_STOP_AND_TAKE_PROFIT",
                        "params": {},
                    }
                )
            elif slp is None:
                hints.append(
                    {"severity": "info", "code": "NO_STOP_LOSS", "params": {}}
                )
            elif tpp is None:
                hints.append(
                    {"severity": "info", "code": "NO_TAKE_PROFIT", "params": {}}
                )
            elif slp == 0 and tpp == 0:
                hints.append(
                    {
                        "severity": "info",
                        "code": "ZERO_STOP_AND_TAKE_PROFIT",
                        "params": {},
                    }
                )

            ep = cfg.get("entryPct")
            if ep is not None:
                if ep < 0.15:
                    hints.append(
                        {
                            "severity": "warn",
                            "code": "ENTRY_PCT_VERY_LOW",
                            "params": {"pct": f"{ep * 100:.1f}"},
                        }
                    )
            if cfg.get("trailingEnabled"):
                tpct = cfg.get("trailingStopPct")
                if tpct is None or tpct == 0:
                    hints.append(
                        {
                            "severity": "warn",
                            "code": "TRAILING_NO_PCT",
                            "params": {},
                        }
                    )

    # Optional: obviously empty visualization (starter template style)
    if re.search(r"['\"]plots['\"]\s*:\s*\[\s*\]", raw) and re.search(
        r"['\"]signals['\"]\s*:\s*\[\s*\]", raw
    ):
        codes = {h["code"] for h in hints}
        if "MISSING_OUTPUT" not in codes:
            hints.append(
                {"severity": "info", "code": "EMPTY_PLOTS_AND_SIGNALS", "params": {}}
            )

    return hints
