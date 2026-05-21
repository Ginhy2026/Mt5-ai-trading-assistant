import argparse
import time
from datetime import datetime

from ai.hermes_client import HermesClient
from analytics.daily_review import start_daily_review_scheduler
from config.settings import load_settings
from indicators.technical import add_indicators, latest_indicator_snapshot
from mt5_client import MT5Client
from notifier.feishu import FeishuNotifier
from strategies.key_levels import detect_key_level_signal
from trade_monitor.position_tracker import PositionTracker


def _fetch_tf(mt5_client: MT5Client, symbol: str, timeframe: str, bars: int) -> tuple:
    candles = mt5_client.get_candles(symbol, timeframe, bars)
    candles = add_indicators(candles).dropna()
    if candles.empty:
        raise RuntimeError(f"Not enough candle data to calculate indicators for {timeframe}.")

    indicators = latest_indicator_snapshot(candles)
    latest = candles.iloc[-1]
    snapshot = {
        "timeframe": timeframe,
        "close": round(indicators["close"], 3),
        "rsi": round(indicators["rsi"], 2),
        "ema20": round(indicators["ema20"], 3),
        "ema50": round(indicators["ema50"], 3),
        "atr": round(indicators["atr"], 3),
        "high": round(float(latest["high"]), 3),
        "low": round(float(latest["low"]), 3),
    }
    return candles, snapshot


def analyze_once(settings, mt5_client: MT5Client, hermes: HermesClient, notifier: FeishuNotifier) -> bool:
    tick = mt5_client.get_tick(settings.mt5_symbol)
    _, direction_tf = _fetch_tf(
        mt5_client,
        settings.mt5_symbol,
        settings.mt5_tf_direction,
        settings.mt5_tf_direction_bars,
    )
    _, swing_tf = _fetch_tf(
        mt5_client,
        settings.mt5_symbol,
        settings.mt5_tf_swing,
        settings.mt5_tf_swing_bars,
    )
    entry_candles, entry_tf = _fetch_tf(
        mt5_client,
        settings.mt5_symbol,
        settings.mt5_tf_entry,
        settings.mt5_tf_entry_bars,
    )

    signal = detect_key_level_signal(
        candles=entry_candles,
        current_price=tick.mid,
        lookback=settings.key_level_lookback,
        atr_multiplier=settings.key_level_atr_multiplier,
        price_pct=settings.key_level_price_pct,
    )

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = (
        f"[{now}] {settings.mt5_symbol} "
        f"{direction_tf['timeframe']}/{swing_tf['timeframe']}/{entry_tf['timeframe']} "
        f"price={tick.mid:.3f}, trend={signal.trend}, "
        f"support={signal.nearest_support:.3f}, resistance={signal.nearest_resistance:.3f}, "
        f"nearest={signal.nearest_level:.3f}({signal.level_type}), "
        f"distance={signal.distance:.3f}, threshold={signal.threshold:.3f}"
    )

    if not signal.is_near_key_level:
        print(f"{status} -> waiting")
        return False

    print(f"{status} -> near key level, asking Hermes")
    context = {
        "symbol": settings.mt5_symbol,
        "current_price": round(tick.mid, 3),
        "bid": round(tick.bid, 3),
        "ask": round(tick.ask, 3),
        "direction": direction_tf,
        "swing": swing_tf,
        "entry": entry_tf,
        "trend": signal.trend,
        "nearest_support": round(signal.nearest_support, 3),
        "nearest_resistance": round(signal.nearest_resistance, 3),
        "nearest_level": round(signal.nearest_level, 3),
        "level_type": signal.level_type,
        "distance": round(signal.distance, 3),
        "threshold": round(signal.threshold, 3),
        "is_near_key_level": signal.is_near_key_level,
    }
    report = hermes.generate_analysis(context)
    notifier.send_markdown_report(report)
    print(report)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor MT5 market data and send AI alerts near key levels.")
    parser.add_argument("--once", action="store_true", help="Run one monitor cycle and exit.")
    parser.add_argument("--with-tracker", action="store_true", help="Start position tracker and daily review scheduler.")
    args = parser.parse_args()

    settings = load_settings()

    mt5_client = MT5Client(
        login=settings.mt5_login,
        password=settings.mt5_password,
        server=settings.mt5_server,
        path=settings.mt5_path,
    )
    hermes = HermesClient(
        api_url=settings.hermes_api_url,
        model=settings.hermes_model,
        api_key=settings.hermes_api_key,
        timeout=settings.hermes_timeout,
    )
    notifier = FeishuNotifier(
        webhook_url=settings.feishu_webhook_url,
        secret=settings.feishu_secret,
    )
    tracker = None
    scheduler = None

    try:
        mt5_client.connect()
        print(
            "Monitor started: "
            f"symbol={settings.mt5_symbol}, "
            f"direction={settings.mt5_tf_direction}/{settings.mt5_tf_direction_bars}, "
            f"swing={settings.mt5_tf_swing}/{settings.mt5_tf_swing_bars}, "
            f"entry={settings.mt5_tf_entry}/{settings.mt5_tf_entry_bars}, "
            f"interval={settings.monitor_interval_seconds}s, "
            f"cooldown={settings.alert_cooldown_seconds}s"
        )
        if args.with_tracker:
            tracker = PositionTracker(settings.trade_db_path, settings.position_poll_interval)
            tracker.start()
            scheduler = start_daily_review_scheduler(settings)

        if args.once:
            analyze_once(settings, mt5_client, hermes, notifier)
            return

        last_alert_at = 0.0
        while True:
            try:
                cooldown_left = settings.alert_cooldown_seconds - (time.time() - last_alert_at)
                if cooldown_left > 0:
                    print(f"Alert cooldown active. Next AI alert allowed in {cooldown_left:.0f}s")
                else:
                    alerted = analyze_once(settings, mt5_client, hermes, notifier)
                    if alerted:
                        last_alert_at = time.time()
            except Exception as exc:
                print(f"Monitor cycle failed: {exc}")

            time.sleep(settings.monitor_interval_seconds)
    except KeyboardInterrupt:
        print("Monitoring stopped by user.")
    finally:
        if tracker:
            tracker.stop()
        if scheduler:
            scheduler.shutdown(wait=False)
        mt5_client.shutdown()


if __name__ == "__main__":
    main()
