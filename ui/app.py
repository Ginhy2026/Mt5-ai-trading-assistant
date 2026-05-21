from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from analytics.daily_review import run_daily_review
from ask import ask_market
from config.settings import load_settings
from trade_models import connect_db, find_similar_mistakes, list_trades


st.set_page_config(page_title="MT5 AI Trading Assistant", layout="wide")


def main() -> None:
    settings = load_settings()
    st.title("MT5 AI Trading Assistant")

    tab_ask, tab_trades, tab_mistakes, tab_review = st.tabs(
        ["行情问询", "交易记录", "历史错误", "每日复盘"]
    )
    with tab_ask:
        render_ask(settings)
    with tab_trades:
        render_trades(settings)
    with tab_mistakes:
        render_mistakes(settings)
    with tab_review:
        render_review(settings)


def render_ask(settings) -> None:
    st.subheader("开单前行情检查")
    mode = st.radio("分析模式", ["完整分析", "侧重做多", "侧重做空", "自定义想法"], horizontal=True)
    custom = ""
    if mode == "侧重做多":
        custom = "buy"
    elif mode == "侧重做空":
        custom = "sell"
    elif mode == "自定义想法":
        custom = st.text_area("你的交易想法", placeholder="例如：我想等H4回调到EMA20做多")

    if st.button("询问 Hermes", type="primary"):
        with st.spinner("正在读取行情并询问 Hermes..."):
            try:
                st.markdown(ask_market(settings, custom))
            except Exception as exc:
                st.error(f"问询失败: {exc}")


def render_trades(settings) -> None:
    st.subheader("交易记录")
    limit = st.number_input("显示条数", min_value=20, max_value=1000, value=200, step=20)
    with connect_db(settings.trade_db_path) as conn:
        trades = list_trades(conn, int(limit))
    st.dataframe(_trades_df(trades), use_container_width=True)


def render_mistakes(settings) -> None:
    st.subheader("历史错误检索")
    symbol = st.text_input("品种", value=settings.mt5_symbol)
    direction = st.selectbox("方向", ["", "buy", "sell"])
    signal_type = st.selectbox("信号类型", ["", "黄金共振", "趋势回调", "区间波段", "无明确信号"])
    with connect_db(settings.trade_db_path) as conn:
        trades = find_similar_mistakes(conn, symbol, direction or None, signal_type or None, limit=50)
    st.dataframe(_trades_df(trades), use_container_width=True)


def render_review(settings) -> None:
    st.subheader("每日复盘预览")
    review_date = st.date_input("复盘交易日", value=date.today() - timedelta(days=1))
    write_obsidian = st.checkbox("写入 Obsidian 并尝试 git push", value=False)
    if st.button("生成复盘", type="primary"):
        with st.spinner("正在生成复盘..."):
            try:
                result = run_daily_review(settings, review_date, write_obsidian=write_obsidian)
                st.json(
                    {
                        "trade_date": result.trade_date,
                        "total_trades": result.total_trades,
                        "win_rate": result.win_rate,
                        "total_profit": result.total_profit,
                        "average_profit_loss_ratio": result.average_profit_loss_ratio,
                        "direction_distribution": result.direction_distribution,
                    }
                )
                st.markdown(result.ai_review)
            except Exception as exc:
                st.error(f"复盘失败: {exc}")


def _trades_df(trades) -> pd.DataFrame:
    return pd.DataFrame([trade.__dict__ for trade in trades])


if __name__ == "__main__":
    main()
