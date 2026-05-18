# mt5-ai-trading-assistant

MVP for: **price near key level -> Hermes AI trading analysis -> Feishu alert**.

The first version only analyzes and notifies. It does **not** place orders.

## Features

- Connect to MetaTrader 5.
- Monitor real-time XAUUSD tick price.
- Fetch H4, H1, and M15 candles for multi-timeframe analysis.
- Calculate RSI, EMA20, EMA50, and ATR.
- Detect whether price is near recent support/resistance.
- Ask Hermes for a markdown trading report.
- Push the analysis result to a Feishu webhook.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Then edit `.env`.

At minimum, set:

- `MT5_SYMBOL=XAUUSD+`
- `HERMES_API_URL`
- `HERMES_MODEL`
- `FEISHU_WEBHOOK_URL`

If your MT5 terminal is already logged in, `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` can stay empty.

## Run

Check local configuration first:

```powershell
python -m scripts.check_setup
```

Run one market scan:

```powershell
python main.py --once
```

Start continuous monitoring:

```powershell
python main.py
```

The script keeps running until you press `Ctrl+C`.

Default monitor behavior:

- Scans the market every `MONITOR_INTERVAL_SECONDS=60` seconds.
- Uses `MT5_TF_DIRECTION=H4`, `MT5_TF_SWING=H1`, and `MT5_TF_ENTRY=M15` by default.
- Detects support/resistance on the entry timeframe.
- Calls Hermes only when price is near support/resistance on the entry timeframe.
- Sends at most one alert every `ALERT_COOLDOWN_SECONDS=900` seconds.

Your broker may use suffixed symbols such as `XAUUSD+`, `CL-OIL`, or `EURUSD+`.
Use the exact symbol name shown in MT5 Market Watch.

## Hermes API

This project expects an OpenAI-compatible chat completions endpoint:

```http
POST /v1/chat/completions
```

Example body:

```json
{
  "model": "hermes",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ]
}
```

If your Hermes service exposes a different API shape, update `ai/hermes_client.py`.

To let a local Hermes service provide its own runtime details, keep secrets out of
the repository and configure these environment variables in `.env`:

- `HERMES_API_URL`
- `HERMES_MODEL`
- `HERMES_API_KEY` if your endpoint requires authentication

## Feishu

The notifier sends a Feishu interactive card containing the markdown report.
If your webhook has signature verification enabled, set `FEISHU_SECRET`.
