from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _optional_int(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    return int(value) if value else None


def _optional_str(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    mt5_login: int | None
    mt5_password: str | None
    mt5_server: str | None
    mt5_path: str | None
    mt5_symbol: str
    mt5_timeframe: str
    mt5_bars: int
    monitor_interval_seconds: int
    alert_cooldown_seconds: int
    key_level_lookback: int
    key_level_atr_multiplier: float
    key_level_price_pct: float
    hermes_api_url: str
    hermes_model: str
    hermes_api_key: str | None
    hermes_timeout: int
    feishu_webhook_url: str | None
    feishu_secret: str | None


def load_settings() -> Settings:
    return Settings(
        mt5_login=_optional_int("MT5_LOGIN"),
        mt5_password=_optional_str("MT5_PASSWORD"),
        mt5_server=_optional_str("MT5_SERVER"),
        mt5_path=_optional_str("MT5_PATH"),
        mt5_symbol=os.getenv("MT5_SYMBOL", "XAUUSD+").strip(),
        mt5_timeframe=os.getenv("MT5_TIMEFRAME", "M15").strip().upper(),
        mt5_bars=int(os.getenv("MT5_BARS", "100")),
        monitor_interval_seconds=int(os.getenv("MONITOR_INTERVAL_SECONDS", "60")),
        alert_cooldown_seconds=int(os.getenv("ALERT_COOLDOWN_SECONDS", "900")),
        key_level_lookback=int(os.getenv("KEY_LEVEL_LOOKBACK", "80")),
        key_level_atr_multiplier=float(os.getenv("KEY_LEVEL_ATR_MULTIPLIER", "0.35")),
        key_level_price_pct=float(os.getenv("KEY_LEVEL_PRICE_PCT", "0.001")),
        hermes_api_url=os.getenv("HERMES_API_URL", "http://localhost:11434/v1/chat/completions").strip(),
        hermes_model=os.getenv("HERMES_MODEL", "hermes").strip(),
        hermes_api_key=_optional_str("HERMES_API_KEY"),
        hermes_timeout=int(os.getenv("HERMES_TIMEOUT", "60")),
        feishu_webhook_url=_optional_str("FEISHU_WEBHOOK_URL"),
        feishu_secret=_optional_str("FEISHU_SECRET"),
    )
