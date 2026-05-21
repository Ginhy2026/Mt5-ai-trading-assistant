from __future__ import annotations

from datetime import date, datetime, timedelta

import requests
from apscheduler.schedulers.background import BackgroundScheduler

from config.settings import Settings
from output.obsidian_journal import write_daily_review_to_obsidian
from trade_models import DailyReviewResult, connect_db, list_closed_trades_for_date, summarize_closed_trades


def run_daily_review(settings: Settings, trade_date: date | None = None, write_obsidian: bool = True) -> DailyReviewResult:
    review_date = trade_date or (date.today() - timedelta(days=1))
    with connect_db(settings.trade_db_path) as conn:
        trades = list_closed_trades_for_date(conn, review_date)
        summary = summarize_closed_trades(trades)

    ai_review = _generate_ai_review(settings, review_date, summary, trades)
    result = DailyReviewResult(
        trade_date=review_date.isoformat(),
        trades=trades,
        ai_review=ai_review,
        **summary,
    )

    if write_obsidian:
        try:
            path = write_daily_review_to_obsidian(
                result,
                settings.obsidian_vault_path,
                settings.obsidian_trade_dir,
            )
            print(f"Daily review written: {path}")
        except Exception as exc:
            print(f"Failed to write Obsidian daily review: {exc}")

    return result


def start_daily_review_scheduler(settings: Settings) -> BackgroundScheduler:
    hour, minute = _parse_review_time(settings.daily_review_time)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: run_daily_review(settings),
        "cron",
        hour=hour,
        minute=minute,
        id="daily-trading-review",
        replace_existing=True,
    )
    scheduler.start()
    print(f"Daily review scheduler started: {settings.daily_review_time}")
    return scheduler


def _parse_review_time(value: str) -> tuple[int, int]:
    hour_text, minute_text = value.split(":", 1)
    return int(hour_text), int(minute_text)


def _generate_ai_review(settings: Settings, review_date: date, summary: dict, trades: list) -> str:
    trade_lines = "\n".join(
        f"- {trade.ticket} {trade.symbol} {trade.direction} volume={trade.volume} "
        f"open={trade.open_price} close={trade.close_price} profit={trade.profit} "
        f"reason={trade.entry_reason or '未填写'} mistakes={trade.mistake_tags or '未填写'}"
        for trade in trades
    ) or "- 当日无已平仓交易"

    prompt = f"""
请基于以下 MT5 当日交易数据生成中文交易复盘。

交易日: {review_date.isoformat()}
统计:
- 交易次数: {summary["total_trades"]}
- 胜率: {summary["win_rate"]:.2f}%
- 总盈亏: {summary["total_profit"]:.2f}
- 平均盈亏: {summary["average_profit"]:.2f}
- 平均盈亏比: {summary["average_profit_loss_ratio"]:.2f}
- 方向分布: {summary["direction_distribution"]}
- 最大单笔盈利: {summary["max_profit"]:.2f}
- 最大单笔亏损: {summary["max_loss"]:.2f}

交易明细:
{trade_lines}

请输出:
1. 今天哪里做得好
2. 今天哪里做错了
3. 是否出现重复错误
4. 明天需要注意什么
5. 一句执行纪律提醒
"""
    return _call_hermes(settings, prompt)


def _call_hermes(settings: Settings, prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if settings.hermes_api_key:
        headers["Authorization"] = f"Bearer {settings.hermes_api_key}"

    payload = {
        "model": settings.hermes_model,
        "messages": [
            {"role": "system", "content": "You are a strict trading journal reviewer. Reply in Chinese markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    response = requests.post(settings.hermes_api_url, json=payload, headers=headers, timeout=settings.hermes_timeout)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
