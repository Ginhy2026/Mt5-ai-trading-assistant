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
请基于以下多时间框架市场数据生成结构化交易信号报告，并先判断信号类型。

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

信号类型定义:

【黄金共振】
- 条件: H4 和 H1 方向一致（都是多头或都是空头）+ M15 价格靠近对应方向的关键位。
- 策略: 顺大势顺小势，方向明确，可以稍微积极。
- 止损: 做多时设在最近支撑下方 1.5×ATR；做空时设在最近阻力上方 1.5×ATR。
- 止盈: TP1=最近反向关键位，TP2=EMA50/H1 波段目标，TP3=前高/前低。

【趋势回调】
- 条件: H4 有明确方向（多头或空头）+ H1 方向相反（回调/反弹阶段）+ M15 靠近 H4 方向的关键位。
- 策略: 顺大势逆小势，等待回调入场，止损更近，盈亏比通常更好。
- 强度提示: 注意 H1 是否已经回调到 H4 的 EMA20/EMA50 附近，如果是则信号更强。
- 止损: 做多时设在 H1 回调低点下方；做空时设在 H1 反弹高点上方，采用紧止损。
- 止盈: TP1=反向关键位，TP2=前高/前低（趋势延续目标），TP3=H4 EMA50/波段扩展目标。

【区间波段】
- 条件: H4 没有明确方向（震荡/横盘，价格在 EMA20 和 EMA50 之间来回）+ H1 在固定区间内上下波动 + M15 靠近区间边界。
- 策略: 高抛低吸，区间交易，止盈目标设在对侧的区间边界。
- 止损: 设在区间边界外侧 0.5×ATR。
- 止盈: TP1=区间中线，TP2=对侧区间边界，TP3=区间边界外 1×ATR。

【无明确信号】
- 条件: 以上都不满足，或 H4/H1/M15 方向冲突且没有清晰关键位。
- 结论: 建议等待。

输出格式:
请只输出 markdown，并严格按以下 10 个板块排序。如果方向冲突或不明确，在对应板块里注明“无明确信号”。

1. 📋 信号类型 + 策略描述
   - 📋 **信号类型**: 黄金共振 / 趋势回调 / 区间波段 / 无明确信号
   - 📝 **策略描述**: 一句话描述当前策略，例如“顺 H4 趋势，等 H1 回调入场”
2. 📊 多时间框架分析（H4/H1/M15 分别一句话）
3. 📈 信号方向（做多 / 做空 / 观望）
4. 🎯 入场区间（注明是基于什么逻辑）
5. 🛑 止损位（注明止损依据）
6. ✅ 止盈目标 1/2/3（注明目标依据）
7. ⚠️ 风险等级（低/中/高）
8. 💰 盈亏比
9. 🔍 关键观察
10. 📝 结论（等待 / 观察 / 轻仓尝试）

要求:
1. 只输出 markdown 报告。
2. 先判断大方向趋势，再看波段，最后给出入场建议。
3. 三个时间框架方向一致可适当积极，方向冲突则保守等待。
4. 不要自动下单，不要给绝对化结论。
5. 结论必须在“等待 / 观察 / 轻仓尝试”中选择一个。
6. 如果当前价格没有接近关键位，必须建议等待或观察。
7. 必须先判断信号类型（黄金共振/趋势回调/区间波段/无明确信号），再根据信号类型制定策略。
8. 不同类型信号的止损和止盈逻辑不同，在报告里注明依据。
9. 趋势回调策略盈亏比通常优于黄金共振，因为止损更近。
10. 如果判断为区间波段，一定要确认 H4 没有明确趋势方向（价格在 EMA20 和 EMA50 之间来回）。
11. 必须给出具体的做多/做空方向、入场区间、止损位、三个止盈目标；如果没有明确信号，方向写“观望”，价格位仍按最近关键位给出参考。
12. 盈亏比至少 1:2 才建议轻仓尝试，否则建议等待。
"""


def _tf_block(label: str, tf: dict) -> str:
    return f"""时间框架 - {label} ({tf["timeframe"]}):
- Close: {tf["close"]}
- RSI14: {tf["rsi"]}
- EMA20: {tf["ema20"]}
- EMA50: {tf["ema50"]}
- ATR14: {tf["atr"]}
- 最新K线高点: {tf["high"]}
- 最新K线低点: {tf["low"]}
- 趋势参考: Close 高于 EMA20/EMA50 偏多，低于 EMA20/EMA50 偏空，夹在 EMA20/EMA50 之间偏震荡"""
