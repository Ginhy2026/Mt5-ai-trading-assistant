from __future__ import annotations

import subprocess
from pathlib import Path

from trade_models import DailyReviewResult, TradeRecord


def write_daily_review_to_obsidian(result: DailyReviewResult, vault_path: str, trade_dir: str) -> Path:
    vault = Path(vault_path)
    if not vault.exists():
        raise FileNotFoundError(f"Obsidian vault not found: {vault}")

    journal_dir = vault / trade_dir
    journal_dir.mkdir(parents=True, exist_ok=True)
    file_path = journal_dir / f"{result.trade_date}-交易复盘.md"
    file_path.write_text(_build_markdown(result), encoding="utf-8")
    _commit_and_push(vault, file_path)
    return file_path


def _build_markdown(result: DailyReviewResult) -> str:
    trades_markdown = "\n".join(_trade_line(trade) for trade in result.trades) or "- 当日无已平仓交易"
    direction_distribution = ", ".join(
        f"{direction}: {count}" for direction, count in result.direction_distribution.items()
    ) or "无"

    return f"""---
date: {result.trade_date}
type: trading-review
source: mt5-ai-trading-assistant
tags:
  - trading
  - review
  - mt5
---

# {result.trade_date} 交易复盘

## 当日概况

| 指标 | 数值 |
|---|---:|
| 交易次数 | {result.total_trades} |
| 胜率 | {result.win_rate:.2f}% |
| 总盈亏 | {result.total_profit:.2f} |
| 平均盈亏 | {result.average_profit:.2f} |
| 平均盈亏比 | {result.average_profit_loss_ratio:.2f} |
| 盈利笔数 | {result.wins} |
| 亏损笔数 | {result.losses} |
| 方向分布 | {direction_distribution} |
| 最大单笔盈利 | {result.max_profit:.2f} |
| 最大单笔亏损 | {result.max_loss:.2f} |

## 交易明细

{trades_markdown}

## AI 复盘分析

{result.ai_review}
"""


def _trade_line(trade: TradeRecord) -> str:
    return (
        f"- `{trade.ticket}` {trade.symbol} {trade.direction} {trade.volume}手 | "
        f"开仓 {trade.open_price} @ {trade.open_time} | "
        f"平仓 {trade.close_price} @ {trade.close_time} | "
        f"盈亏 {trade.profit}"
    )


def _commit_and_push(vault: Path, file_path: Path) -> None:
    if not (vault / ".git").exists():
        print(f"Obsidian vault is not a git repository, skipped push: {vault}")
        return

    relative_path = str(file_path.relative_to(vault))
    commands = [
        ["git", "add", relative_path],
        ["git", "commit", "-m", f"Add trading review {file_path.stem}"],
        ["git", "push"],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=vault, text=True, capture_output=True)
        if result.returncode != 0:
            output = (result.stderr or result.stdout).strip()
            print(f"Obsidian git command failed ({' '.join(command)}): {output}")
            return
