from __future__ import annotations

import requests


SYSTEM_PROMPT = """You are Hermes, a cautious multi-timeframe trading analysis assistant.
You analyze direction timeframe, swing timeframe, entry timeframe, key levels, indicators, and risk.
Never claim certainty. Do not recommend automatic order placement.
Return concise markdown in Chinese with structured trading signal sections.
"""


class HermesClient:
    def __init__(self, api_url: str, model: str, api_key: str | None = None, timeout: int = 60) -> None:
        self.api_url = api_url
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def generate_analysis(self, market_context: dict) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(market_context)},
            ],
            "temperature": 0.2,
        }
        response = requests.post(self.api_url, json=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


def _build_user_prompt(context: dict) -> str:
    return f"""
请基于以下多时间框架市场数据生成结构化交易信号报告。

交易品种: {context["symbol"]}
当前价格: {context["current_price"]}
Bid: {context["bid"]}
Ask: {context["ask"]}

{_tf_block("大方向", context["direction"])}

{_tf_block("波段", context["swing"])}

{_tf_block("入场", context["entry"])}

关键位:
- 入场周期趋势判断: {context["trend"]}
- 最近支撑: {context["nearest_support"]}
- 最近阻力: {context["nearest_resistance"]}
- 最近关键位: {context["nearest_level"]} ({context["level_type"]})
- 距离关键位: {context["distance"]}
- 接近阈值: {context["threshold"]}
- 是否接近关键位: {context["is_near_key_level"]}

输出格式:
请只输出 markdown，并包含以下 10 个板块。如果方向冲突或不明确，在对应板块里注明“无明确信号”。

1. 📊 多时间框架分析（H4/H1/M15 分别一句话）
2. 📈 信号方向（做多 / 做空 / 观望）
3. 🎯 入场区间（给出一个价格区间，基于 M15 关键位）
4. 🛑 止损位（基于 ATR 计算，通常止损设在最近支撑下方或阻力上方）
5. ✅ 止盈目标 1/2/3（基于最近的支撑阻力位，给三个目标）
6. ⚠️ 风险等级（低/中/高）
7. 💰 盈亏比（估算入场到止盈1 ÷ 入场到止损）
8. 🔍 关键观察（一句话总结）
9. 📝 结论（等待 / 观察 / 轻仓尝试）
10. 📌 执行提醒（说明这是分析提醒，不是自动下单）

要求:
1. 只输出 markdown 报告。
2. 先判断大方向趋势，再看波段，最后给出入场建议。
3. 三个时间框架方向一致可适当积极，方向冲突则保守等待。
4. 不要自动下单，不要给绝对化结论。
5. 结论必须在“等待 / 观察 / 轻仓尝试”中选择一个。
6. 如果当前价格没有接近关键位，必须建议等待或观察。
7. 必须给出具体的做多/做空方向、入场区间、止损位、三个止盈目标；如果没有明确信号，方向写“观望”，价格位仍按最近关键位给出参考。
8. 止损位根据 ATR 和最近支撑/阻力计算，止盈目标取最近的支撑阻力位或按 ATR 延展目标。
9. 盈亏比至少 1:2 才建议轻仓尝试，否则建议等待。
"""


def _tf_block(label: str, tf: dict) -> str:
    return f"""时间框架 - {label} ({tf["timeframe"]}):
- Close: {tf["close"]}
- RSI14: {tf["rsi"]}
- EMA20: {tf["ema20"]}
- EMA50: {tf["ema50"]}
- ATR14: {tf["atr"]}
- 最新K线高点: {tf["high"]}
- 最新K线低点: {tf["low"]}"""
