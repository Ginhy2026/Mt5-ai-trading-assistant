from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5

from trade_models import TradeRecord, close_trade, connect_db, list_open_trades, upsert_open_trade


class PositionTracker:
    def __init__(self, db_path: str, poll_interval: int = 10) -> None:
        self.db_path = db_path
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self.run, name="position-tracker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def run(self) -> None:
        print(f"Position tracker started: db={self.db_path}, interval={self.poll_interval}s")
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                print(f"Position tracker cycle failed: {exc}")
            self._stop_event.wait(self.poll_interval)

    def poll_once(self) -> None:
        positions = mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"MT5 positions_get failed: {mt5.last_error()}")

        active_tickets = {int(position.ticket) for position in positions}
        with connect_db(self.db_path) as conn:
            for position in positions:
                added = upsert_open_trade(conn, _position_to_trade(position))
                if added:
                    print(f"Tracked new position: ticket={position.ticket}, symbol={position.symbol}")

            for trade in list_open_trades(conn):
                if trade.ticket not in active_tickets:
                    close_info = _find_close_deal(trade)
                    if close_info:
                        closed = close_trade(conn, trade.ticket, **close_info)
                        if closed:
                            print(f"Closed tracked position: ticket={trade.ticket}, profit={close_info['profit']:.2f}")


def _position_to_trade(position) -> TradeRecord:
    direction = "buy" if int(position.type) == mt5.POSITION_TYPE_BUY else "sell"
    open_time = datetime.fromtimestamp(int(position.time)).isoformat(timespec="seconds")
    return TradeRecord(
        ticket=int(position.ticket),
        symbol=str(position.symbol),
        direction=direction,
        volume=float(position.volume),
        open_price=float(position.price_open),
        open_time=open_time,
        status="open",
    )


def _find_close_deal(trade: TradeRecord) -> dict | None:
    open_time = datetime.fromisoformat(trade.open_time)
    from_time = open_time - timedelta(days=2)
    to_time = datetime.now() + timedelta(minutes=5)
    deals = mt5.history_deals_get(from_time, to_time)
    if deals is None:
        raise RuntimeError(f"MT5 history_deals_get failed: {mt5.last_error()}")

    matching = []
    for deal in deals:
        position_id = int(getattr(deal, "position_id", 0))
        if position_id != trade.ticket:
            continue
        entry = int(getattr(deal, "entry", -1))
        profit = float(getattr(deal, "profit", 0.0))
        if entry in {mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY} or profit != 0:
            matching.append(deal)

    if not matching:
        return None

    close_deal = sorted(matching, key=lambda item: int(item.time))[-1]
    close_dt = datetime.fromtimestamp(int(close_deal.time))
    return {
        "close_price": float(close_deal.price),
        "close_time": close_dt.isoformat(timespec="seconds"),
        "profit": float(close_deal.profit),
        "duration_seconds": int((close_dt - open_time).total_seconds()),
    }
