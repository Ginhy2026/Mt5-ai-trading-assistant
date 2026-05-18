from __future__ import annotations

import requests


SYSTEM_PROMPT = """You are Hermes, a cautious trading analysis assistant.
You analyze market context, key levels, indicators, and risk.
Never claim certainty. Do not recommend automatic order placement.
Return concise markdown in Chinese with these sections:
- 当前趋势
- 支撑阻力
- 是否值得交易
- 风险等级
- 建议等待 / 观察 / 轻仓尝试
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
请基于以下市场数据生成交易分析报告。

交易品种: {context["symbol"]}
周期: {context["timeframe"]}
当前价格: {context["current_price"]}
Bid: {context["bid"]}
Ask: {context["ask"]}

指标:
- RSI14: {context["rsi"]}
- EMA20: {context["ema20"]}
- EMA50: {context["ema50"]}
- ATR14: {context["atr"]}

关键位:
- 趋势判断: {context["trend"]}
- 最近支撑: {context["nearest_support"]}
- 最近阻力: {context["nearest_resistance"]}
- 最近关键位: {context["nearest_level"]} ({context["level_type"]})
- 距离关键位: {context["distance"]}
- 接近阈值: {context["threshold"]}
- 是否接近关键位: {context["is_near_key_level"]}

要求:
1. 只输出 markdown 报告。
2. 不要自动下单，不要给绝对化结论。
3. 结论必须在“建议等待 / 观察 / 轻仓尝试”中选择一个。
"""
