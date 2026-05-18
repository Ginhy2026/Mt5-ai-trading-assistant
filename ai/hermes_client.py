from __future__ import annotations

import requests


SYSTEM_PROMPT = """You are Hermes, a cautious multi-timeframe trading analysis assistant.
You analyze direction timeframe, swing timeframe, entry timeframe, key levels, indicators, and risk.
Never claim certainty. Do not recommend automatic order placement.
Return concise markdown in Chinese with exactly these six sections:
- 📊 多时间框架分析
- 📈 当前趋势
- 🎯 支撑阻力
- ✅ 是否值得交易
- ⚠️ 风险等级
- 💡 建议
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
请基于以下多时间框架市场数据生成交易分析报告。

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

要求:
1. 只输出 markdown 报告。
2. 先判断大方向趋势，再看波段，最后给出入场建议。
3. 三个时间框架方向一致可适当积极，方向冲突则保守等待。
4. 不要自动下单，不要给绝对化结论。
5. 结论必须在“建议等待 / 观察 / 轻仓尝试”中选择一个。
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
