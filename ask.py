from __future__ import annotations

import argparse

import requests

from config.settings import Settings, load_settings
from main import _fetch_tf
from mt5_client import MT5Client
from strategies.key_levels import detect_key_level_signal
from trade_models import TradeRecord, connect_db, find_similar_mistakes


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask Hermes for pre-trade market analysis.")
    parser.add_argument("idea", nargs="*", help="Optional: buy, sell, or your trading idea.")
    args = parser.parse_args()
    user_input = " ".join(args.idea).strip()

    settings = load_settings()
    report = ask_market(settings, user_input)
    print(report)


def ask_market(settings: Settings, user_input: str = "") -> str:
    mt5_client = MT5Client(
        login=settings.mt5_login,
        password=settings.mt5_password,
        server=settings.mt5_server,
        path=settings.mt5_path,
    )
    try:
        mt5_client.connect()
        context = build_market_context(settings, mt5_client, user_input)
        mistakes = load_similar_mistakes(settings, context, user_input)
        return _call_hermes(settings, _build_ask_prompt(context, mistakes, user_input))
    finally:
        mt5_client.shutdown()


def build_market_context(settings: Settings, mt5_client: MT5Client, user_input: str = "") -> dict:
    tick = mt5_client.get_tick(settings.mt5_symbol)
    _, direction_tf = _fetch_tf(
        mt5_client,
        settings.mt5_symbol,
        settings.mt5_tf_direction,
        settings.mt5_tf_direction_bars,
    )
    _, swing_tf = _fetch_tf(
        mt5_client,
        settings.mt5_symbol,
        settings.mt5_tf_swing,
        settings.mt5_tf_swing_bars,
    )
    entry_candles, entry_tf = _fetch_tf(
        mt5_client,
        settings.mt5_symbol,
        settings.mt5_tf_entry,
        settings.mt5_tf_entry_bars,
    )
    signal = detect_key_level_signal(
        candles=entry_candles,
        current_price=tick.mid,
        lookback=settings.key_level_lookback,
        atr_multiplier=settings.key_level_atr_multiplier,
        price_pct=settings.key_level_price_pct,
    )
    return {
        "symbol": settings.mt5_symbol,
        "current_price": round(tick.mid, 3),
        "bid": round(tick.bid, 3),
        "ask": round(tick.ask, 3),
        "direction": direction_tf,
        "swing": swing_tf,
        "entry": entry_tf,
        "trend": signal.trend,
        "nearest_support": round(signal.nearest_support, 3),
        "nearest_resistance": round(signal.nearest_resistance, 3),
        "nearest_level": round(signal.nearest_level, 3),
        "level_type": signal.level_type,
        "distance": round(signal.distance, 3),
        "threshold": round(signal.threshold, 3),
        "is_near_key_level": signal.is_near_key_level,
        "bias": _parse_bias(user_input),
    }


def load_similar_mistakes(settings: Settings, context: dict, user_input: str = "") -> list[TradeRecord]:
    with connect_db(settings.trade_db_path) as conn:
        return find_similar_mistakes(
            conn,
            symbol=context["symbol"],
            direction=_parse_bias(user_input),
            limit=8,
        )


def _parse_bias(user_input: str) -> str | None:
    text = user_input.strip().lower()
    if text == "buy" or "做多" in text or "多" == text:
        return "buy"
    if text == "sell" or "做空" in text or "空" == text:
        return "sell"
    return None


def _build_ask_prompt(context: dict, mistakes: list[TradeRecord], user_input: str) -> str:
    mode = "完整多时间框架分析"
    if context["bias"] == "buy":
        mode = "侧重做多逻辑"
    elif context["bias"] == "sell":
        mode = "侧重做空逻辑"
    elif user_input:
        mode = "评估用户自定义交易想法"

    mistake_text = "\n".join(_mistake_line(trade) for trade in mistakes) or "暂无相似交易记录"
    user_idea = user_input or "无"
    return f"""
请做开单前行情检查。模式: {mode}

用户想法: {user_idea}

市场数据:
- 品种: {context["symbol"]}
- 当前价格: {context["current_price"]}
- Bid/Ask: {context["bid"]} / {context["ask"]}
- H4大方向: {context["direction"]}
- H1波段: {context["swing"]}
- M15入场: {context["entry"]}

关键位:
- 入场周期趋势: {context["trend"]}
- 最近支撑: {context["nearest_support"]}
- 最近阻力: {context["nearest_resistance"]}
- 最近关键位: {context["nearest_level"]} ({context["level_type"]})
- 距离关键位: {context["distance"]}
- 接近阈值: {context["threshold"]}
- 是否接近关键位: {context["is_near_key_level"]}

历史相似亏损/错误记录:
{mistake_text}

请输出中文 markdown:
1. 当前是否适合交易
2. 做多逻辑
3. 做空逻辑
4. 用户想法是否合理
5. 历史错误提醒
6. 需要等待的条件
7. 最终结论: 等待 / 观察 / 轻仓尝试
"""


def _mistake_line(trade: TradeRecord) -> str:
    return (
        f"- {trade.close_time} {trade.symbol} {trade.direction} profit={trade.profit} "
        f"signal={trade.signal_type or '未填'} mistakes={trade.mistake_tags or '未填'} "
        f"lesson={trade.lesson or '未填'}"
    )


def _call_hermes(settings: Settings, prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if settings.hermes_api_key:
        headers["Authorization"] = f"Bearer {settings.hermes_api_key}"

    payload = {
        "model": settings.hermes_model,
        "messages": [
            {"role": "system", "content": "You are a cautious pre-trade checklist assistant. Reply in Chinese markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    response = requests.post(settings.hermes_api_url, json=payload, headers=headers, timeout=settings.hermes_timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


if __name__ == "__main__":
    main()
