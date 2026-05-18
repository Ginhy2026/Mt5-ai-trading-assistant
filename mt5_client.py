from __future__ import annotations

from dataclasses import dataclass

import MetaTrader5 as mt5
import pandas as pd


TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


@dataclass(frozen=True)
class TickPrice:
    bid: float
    ask: float
    last: float
    time: int

    @property
    def mid(self) -> float:
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return self.last


class MT5Client:
    def __init__(
        self,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        path: str | None = None,
    ) -> None:
        self.login = login
        self.password = password
        self.server = server
        self.path = path

    def connect(self) -> None:
        init_kwargs = {}
        if self.path:
            init_kwargs["path"] = self.path
        if not mt5.initialize(**init_kwargs):
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

        if self.login and self.password and self.server:
            if not mt5.login(self.login, password=self.password, server=self.server):
                raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")

    def shutdown(self) -> None:
        mt5.shutdown()

    def ensure_symbol(self, symbol: str) -> None:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol not found in MT5: {symbol}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Failed to select symbol in Market Watch: {symbol}")

    def get_tick(self, symbol: str) -> TickPrice:
        self.ensure_symbol(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Failed to get tick for {symbol}: {mt5.last_error()}")
        return TickPrice(
            bid=float(tick.bid),
            ask=float(tick.ask),
            last=float(tick.last),
            time=int(tick.time),
        )

    def get_candles(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        self.ensure_symbol(symbol)
        mt5_timeframe = TIMEFRAMES.get(timeframe.upper())
        if mt5_timeframe is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {', '.join(TIMEFRAMES)}")

        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Failed to get candles for {symbol}: {mt5.last_error()}")

        data = pd.DataFrame(rates)
        data["time"] = pd.to_datetime(data["time"], unit="s")
        return data
