from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class TradeRecord:
    ticket: int
    symbol: str
    direction: str
    volume: float
    open_price: float
    open_time: str
    status: str
    close_price: float | None = None
    close_time: str | None = None
    profit: float | None = None
    duration_seconds: int | None = None
    signal_type: str | None = None
    entry_reason: str | None = None
    mistake_tags: str | None = None
    lesson: str | None = None


@dataclass(frozen=True)
class DailyReviewResult:
    trade_date: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_profit: float
    average_profit: float
    average_profit_loss_ratio: float
    direction_distribution: dict[str, int]
    max_profit: float
    max_loss: float
    trades: list[TradeRecord]
    ai_review: str


def connect_db(db_path: str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            ticket INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            volume REAL NOT NULL,
            open_price REAL NOT NULL,
            open_time TEXT NOT NULL,
            close_price REAL,
            close_time TEXT,
            profit REAL,
            duration_seconds INTEGER,
            status TEXT NOT NULL DEFAULT 'open',
            signal_type TEXT,
            entry_reason TEXT,
            mistake_tags TEXT,
            lesson TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def upsert_open_trade(conn: sqlite3.Connection, trade: TradeRecord) -> bool:
    existing = conn.execute("SELECT ticket FROM trades WHERE ticket = ?", (trade.ticket,)).fetchone()
    if existing:
        return False

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO trades (
            ticket, symbol, direction, volume, open_price, open_time, status,
            signal_type, entry_reason, mistake_tags, lesson, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
        """,
        (
            trade.ticket,
            trade.symbol,
            trade.direction,
            trade.volume,
            trade.open_price,
            trade.open_time,
            trade.signal_type,
            trade.entry_reason,
            trade.mistake_tags,
            trade.lesson,
            now,
            now,
        ),
    )
    conn.commit()
    return True


def close_trade(
    conn: sqlite3.Connection,
    ticket: int,
    close_price: float,
    close_time: str,
    profit: float,
    duration_seconds: int,
) -> bool:
    result = conn.execute(
        """
        UPDATE trades
        SET close_price = ?, close_time = ?, profit = ?, duration_seconds = ?,
            status = 'closed', updated_at = ?
        WHERE ticket = ? AND status = 'open'
        """,
        (close_price, close_time, profit, duration_seconds, datetime.now().isoformat(timespec="seconds"), ticket),
    )
    conn.commit()
    return result.rowcount > 0


def list_open_trades(conn: sqlite3.Connection) -> list[TradeRecord]:
    rows = conn.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY open_time").fetchall()
    return [_row_to_trade(row) for row in rows]


def list_trades(conn: sqlite3.Connection, limit: int = 200) -> list[TradeRecord]:
    rows = conn.execute(
        "SELECT * FROM trades ORDER BY open_time DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [_row_to_trade(row) for row in rows]


def list_closed_trades_for_date(conn: sqlite3.Connection, trade_date: date) -> list[TradeRecord]:
    start = trade_date.isoformat()
    end = trade_date.isoformat()
    rows = conn.execute(
        """
        SELECT * FROM trades
        WHERE status = 'closed' AND date(close_time) BETWEEN date(?) AND date(?)
        ORDER BY close_time
        """,
        (start, end),
    ).fetchall()
    return [_row_to_trade(row) for row in rows]


def find_similar_mistakes(
    conn: sqlite3.Connection,
    symbol: str,
    direction: str | None = None,
    signal_type: str | None = None,
    limit: int = 8,
) -> list[TradeRecord]:
    query = ["SELECT * FROM trades WHERE status = 'closed' AND profit < 0 AND symbol = ?"]
    params: list[object] = [symbol]
    if direction:
        query.append("AND direction = ?")
        params.append(direction)
    if signal_type:
        query.append("AND signal_type = ?")
        params.append(signal_type)
    query.append("ORDER BY close_time DESC LIMIT ?")
    params.append(limit)
    rows = conn.execute(" ".join(query), params).fetchall()
    return [_row_to_trade(row) for row in rows]


def summarize_closed_trades(trades: Iterable[TradeRecord]) -> dict:
    trade_list = list(trades)
    wins = [trade for trade in trade_list if (trade.profit or 0) > 0]
    losses = [trade for trade in trade_list if (trade.profit or 0) < 0]
    profits = [trade.profit or 0 for trade in trade_list]
    direction_distribution: dict[str, int] = {}
    for trade in trade_list:
        direction_distribution[trade.direction] = direction_distribution.get(trade.direction, 0) + 1

    total = len(trade_list)
    total_profit = sum(profits)
    average_win = sum((trade.profit or 0) for trade in wins) / len(wins) if wins else 0.0
    average_loss = abs(sum((trade.profit or 0) for trade in losses) / len(losses)) if losses else 0.0
    return {
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / total * 100) if total else 0.0,
        "total_profit": total_profit,
        "average_profit": (total_profit / total) if total else 0.0,
        "average_profit_loss_ratio": (average_win / average_loss) if average_loss else 0.0,
        "direction_distribution": direction_distribution,
        "max_profit": max(profits) if profits else 0.0,
        "max_loss": min(profits) if profits else 0.0,
    }


def _row_to_trade(row: sqlite3.Row) -> TradeRecord:
    return TradeRecord(
        ticket=int(row["ticket"]),
        symbol=str(row["symbol"]),
        direction=str(row["direction"]),
        volume=float(row["volume"]),
        open_price=float(row["open_price"]),
        open_time=str(row["open_time"]),
        close_price=_optional_float(row["close_price"]),
        close_time=row["close_time"],
        profit=_optional_float(row["profit"]),
        duration_seconds=row["duration_seconds"],
        status=str(row["status"]),
        signal_type=row["signal_type"],
        entry_reason=row["entry_reason"],
        mistake_tags=row["mistake_tags"],
        lesson=row["lesson"],
    )


def _optional_float(value: object) -> float | None:
    return float(value) if value is not None else None
