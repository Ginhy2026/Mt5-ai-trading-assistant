from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class KeyLevelSignal:
    is_near_key_level: bool
    nearest_support: float
    nearest_resistance: float
    nearest_level: float
    level_type: str
    distance: float
    threshold: float
    trend: str


def detect_key_level_signal(
    candles: pd.DataFrame,
    current_price: float,
    lookback: int = 80,
    atr_multiplier: float = 0.35,
    price_pct: float = 0.001,
) -> KeyLevelSignal:
    if candles.empty:
        raise ValueError("Cannot detect key levels from empty candles.")

    recent = candles.tail(lookback)
    nearest_support = float(recent["low"].min())
    nearest_resistance = float(recent["high"].max())
    latest_atr = float(recent["atr"].dropna().iloc[-1]) if recent["atr"].notna().any() else 0.0

    support_distance = abs(current_price - nearest_support)
    resistance_distance = abs(nearest_resistance - current_price)

    if support_distance <= resistance_distance:
        nearest_level = nearest_support
        level_type = "support"
        distance = support_distance
    else:
        nearest_level = nearest_resistance
        level_type = "resistance"
        distance = resistance_distance

    threshold = max(latest_atr * atr_multiplier, current_price * price_pct)
    latest = candles.iloc[-1]
    trend = _classify_trend(float(latest["close"]), float(latest["ema20"]), float(latest["ema50"]))

    return KeyLevelSignal(
        is_near_key_level=distance <= threshold,
        nearest_support=nearest_support,
        nearest_resistance=nearest_resistance,
        nearest_level=nearest_level,
        level_type=level_type,
        distance=float(distance),
        threshold=float(threshold),
        trend=trend,
    )


def _classify_trend(close: float, ema20: float, ema50: float) -> str:
    if close > ema20 > ema50:
        return "bullish"
    if close < ema20 < ema50:
        return "bearish"
    return "ranging"
