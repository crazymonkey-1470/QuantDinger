"""
新用户注册时写入内置示例指标（可自由修改、删除）。

通过首条示例名称做幂等：已存在则跳过，避免重复调用 create_user 等边界情况重复插入。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _builtin_specs() -> List[Dict[str, str]]:
    """内置指标：name / description / code（与指标 IDE、回测引擎约定一致）。"""
    return [
        {
            "name": "[示例] RSI 边缘触发",
            "description": "经典 RSI 超卖反弹买入、超买回落卖出；信号为「当根刚触发」避免重复开仓。适合熟悉回测面板与 @strategy。",
            "code": r'''my_indicator_name = "[示例] RSI 边缘触发"
my_indicator_description = "RSI 超卖/超买 + 边缘触发；可在回测面板调杠杆、周期与标的。"

# @strategy stopLossPct 0.03
# @strategy takeProfitPct 0.06
# @strategy entryPct 1
# @strategy tradeDirection long

df = df.copy()
rsi_len = 14
delta = df['close'].diff()
gain = delta.clip(lower=0)
loss = (-delta).clip(lower=0)
avg_gain = gain.ewm(alpha=1 / rsi_len, adjust=False).mean()
avg_loss = loss.ewm(alpha=1 / rsi_len, adjust=False).mean()
rs = avg_gain / avg_loss.replace(0, np.nan)
rsi = 100 - (100 / (1 + rs))
rsi = rsi.fillna(50)

raw_buy = rsi < 30
raw_sell = rsi > 70
buy = raw_buy.fillna(False) & (~raw_buy.shift(1).fillna(False))
sell = raw_sell.fillna(False) & (~raw_sell.shift(1).fillna(False))
df['buy'] = buy.astype(bool)
df['sell'] = sell.astype(bool)

buy_marks = [df['low'].iloc[i] * 0.995 if bool(buy.iloc[i]) else None for i in range(len(df))]
sell_marks = [df['high'].iloc[i] * 1.005 if bool(sell.iloc[i]) else None for i in range(len(df))]

output = {
    'name': my_indicator_name,
    'plots': [
        {'name': 'RSI(14)', 'data': rsi.tolist(), 'color': '#faad14', 'overlay': False}
    ],
    'signals': [
        {'type': 'buy', 'text': 'B', 'data': buy_marks, 'color': '#00E676'},
        {'type': 'sell', 'text': 'S', 'data': sell_marks, 'color': '#FF5252'}
    ]
}
''',
        },
        {
            "name": "[示例] 双均线金叉死叉",
            "description": "快线上穿慢线做多，下穿做空；参数可直接在代码里改 fast/slow 周期。",
            "code": r'''my_indicator_name = "[示例] 双均线金叉死叉"
my_indicator_description = "快慢均线交叉；边缘触发。杠杆、手续费等在回测面板设置。"

# @strategy stopLossPct 0.025
# @strategy takeProfitPct 0.05
# @strategy entryPct 1
# @strategy tradeDirection both

df = df.copy()
fast_n = 12
slow_n = 26
ma_f = df['close'].rolling(fast_n, min_periods=1).mean()
ma_s = df['close'].rolling(slow_n, min_periods=1).mean()

golden = (ma_f > ma_s) & (ma_f.shift(1) <= ma_s.shift(1))
death = (ma_f < ma_s) & (ma_f.shift(1) >= ma_s.shift(1))
df['buy'] = golden.fillna(False).astype(bool)
df['sell'] = death.fillna(False).astype(bool)

buy_marks = [df['low'].iloc[i] * 0.995 if bool(df['buy'].iloc[i]) else None for i in range(len(df))]
sell_marks = [df['high'].iloc[i] * 1.005 if bool(df['sell'].iloc[i]) else None for i in range(len(df))]

output = {
    'name': my_indicator_name,
    'plots': [
        {'name': f'MA({fast_n})', 'data': ma_f.tolist(), 'color': '#1890ff', 'overlay': True},
        {'name': f'MA({slow_n})', 'data': ma_s.tolist(), 'color': '#ff7a45', 'overlay': True}
    ],
    'signals': [
        {'type': 'buy', 'text': 'B', 'data': buy_marks, 'color': '#00E676'},
        {'type': 'sell', 'text': 'S', 'data': sell_marks, 'color': '#FF5252'}
    ]
}
''',
        },
        {
            "name": "[示例] MACD 柱穿零轴",
            "description": "MACD 柱状线由负转正试多，由正转负试空；适合观察动量切换。",
            "code": r'''my_indicator_name = "[示例] MACD 柱穿零轴"
my_indicator_description = "DIF/DEA/柱；柱线穿越零轴边缘触发。可与 1H/4H 加密合约回测配合。"

# @strategy stopLossPct 0.03
# @strategy takeProfitPct 0.08
# @strategy entryPct 0.5
# @strategy tradeDirection both

df = df.copy()
exp12 = df['close'].ewm(span=12, adjust=False).mean()
exp26 = df['close'].ewm(span=26, adjust=False).mean()
dif = exp12 - exp26
dea = dif.ewm(span=9, adjust=False).mean()
hist = dif - dea

raw_buy = (hist > 0) & (hist.shift(1) <= 0)
raw_sell = (hist < 0) & (hist.shift(1) >= 0)
df['buy'] = raw_buy.fillna(False).astype(bool)
df['sell'] = raw_sell.fillna(False).astype(bool)

buy_marks = [df['low'].iloc[i] * 0.995 if bool(df['buy'].iloc[i]) else None for i in range(len(df))]
sell_marks = [df['high'].iloc[i] * 1.005 if bool(df['sell'].iloc[i]) else None for i in range(len(df))]

output = {
    'name': my_indicator_name,
    'plots': [
        {'name': 'MACD DIF', 'data': dif.tolist(), 'color': '#1890ff', 'overlay': False},
        {'name': 'MACD DEA', 'data': dea.tolist(), 'color': '#ff7a45', 'overlay': False},
        {'name': 'MACD Hist', 'data': hist.tolist(), 'color': '#888888', 'overlay': False}
    ],
    'signals': [
        {'type': 'buy', 'text': 'B', 'data': buy_marks, 'color': '#00E676'},
        {'type': 'sell', 'text': 'S', 'data': sell_marks, 'color': '#FF5252'}
    ]
}
''',
        },
        {
            "name": "[示例] 布林带触及",
            "description": "收盘价跌破下轨产生买入信号，突破上轨产生卖出信号（边缘触发）。",
            "code": r'''my_indicator_name = "[示例] 布林带触及"
my_indicator_description = "简单布林带反转思路示例；实盘请结合趋势过滤与风控。"

# @strategy stopLossPct 0.02
# @strategy takeProfitPct 0.04
# @strategy entryPct 0.3
# @strategy tradeDirection long

df = df.copy()
period = 20
mult = 2.0
mid = df['close'].rolling(period, min_periods=1).mean()
std = df['close'].rolling(period, min_periods=1).std()
upper = mid + mult * std
lower = mid - mult * std

raw_buy = df['close'] < lower
raw_sell = df['close'] > upper
buy = raw_buy.fillna(False) & (~raw_buy.shift(1).fillna(False))
sell = raw_sell.fillna(False) & (~raw_sell.shift(1).fillna(False))
df['buy'] = buy.astype(bool)
df['sell'] = sell.astype(bool)

buy_marks = [df['low'].iloc[i] * 0.995 if bool(buy.iloc[i]) else None for i in range(len(df))]
sell_marks = [df['high'].iloc[i] * 1.005 if bool(sell.iloc[i]) else None for i in range(len(df))]

output = {
    'name': my_indicator_name,
    'plots': [
        {'name': 'BOLL 上', 'data': upper.tolist(), 'color': '#69c0ff', 'overlay': True},
        {'name': 'BOLL 中', 'data': mid.tolist(), 'color': '#d9d9d9', 'overlay': True},
        {'name': 'BOLL 下', 'data': lower.tolist(), 'color': '#69c0ff', 'overlay': True}
    ],
    'signals': [
        {'type': 'buy', 'text': 'B', 'data': buy_marks, 'color': '#00E676'},
        {'type': 'sell', 'text': 'S', 'data': sell_marks, 'color': '#FF5252'}
    ]
}
''',
        },
    ]


# 与 _builtin_specs()[0]["name"] 一致，用于注册时幂等判断
_BUILTIN_PACK_ANCHOR_NAME = "[示例] RSI 边缘触发"


def seed_builtin_indicators_for_new_user(db: Any, user_id: int) -> int:
    """
    注册成功后写入示例指标包。若该用户已有锚点名称指标则跳过（幂等）。
    返回本次插入条数。
    """
    if not user_id:
        return 0
    now = int(time.time())
    cur = db.cursor()
    try:
        cur.execute(
            """
            SELECT 1 AS x
            FROM qd_indicator_codes
            WHERE user_id = ? AND name = ?
            LIMIT 1
            """,
            (user_id, _BUILTIN_PACK_ANCHOR_NAME),
        )
        if cur.fetchone():
            return 0

        inserted = 0
        for spec in _builtin_specs():
            cur.execute(
                """
                INSERT INTO qd_indicator_codes
                  (user_id, is_buy, end_time, name, code, description,
                   publish_to_community, pricing_type, price, preview_image, vip_free, review_status,
                   createtime, updatetime, created_at, updated_at)
                VALUES (?, 0, 1, ?, ?, ?, 0, 'free', 0, '', FALSE, NULL, ?, ?, NOW(), NOW())
                """,
                (
                    user_id,
                    spec["name"],
                    spec["code"],
                    spec["description"],
                    now,
                    now,
                ),
            )
            inserted += 1
        db.commit()
        if inserted:
            logger.info("Seeded %s builtin indicator(s) for new user_id=%s", inserted, user_id)
        return inserted
    except Exception as e:
        logger.warning("seed_builtin_indicators_for_new_user failed user_id=%s: %s", user_id, e)
        try:
            db.rollback()
        except Exception:
            pass
        return 0
    finally:
        try:
            cur.close()
        except Exception:
            pass
