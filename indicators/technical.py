import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange


def add_indicators(candles: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = required - set(candles.columns)
    if missing:
        raise ValueError(f"Missing candle columns: {', '.join(sorted(missing))}")

    data = candles.copy()
    data["rsi"] = RSIIndicator(close=data["close"], window=14).rsi()
    data["ema20"] = EMAIndicator(close=data["close"], window=20).ema_indicator()
    data["ema50"] = EMAIndicator(close=data["close"], window=50).ema_indicator()
    data["atr"] = AverageTrueRange(
        high=data["high"],
        low=data["low"],
        close=data["close"],
        window=14,
    ).average_true_range()
    return data


def latest_indicator_snapshot(candles: pd.DataFrame) -> dict:
    latest = candles.iloc[-1]
    return {
        "close": float(latest["close"]),
        "rsi": float(latest["rsi"]),
        "ema20": float(latest["ema20"]),
        "ema50": float(latest["ema50"]),
        "atr": float(latest["atr"]),
    }
