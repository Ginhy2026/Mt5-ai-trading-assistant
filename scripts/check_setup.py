from __future__ import annotations

import sys

import requests

from config.settings import load_settings
from mt5_client import MT5Client


def main() -> int:
    settings = load_settings()
    checks = [
        _check_mt5(settings),
        _check_hermes(settings),
        _check_feishu(settings),
    ]

    print("\nSetup summary")
    for check in checks:
        icon = "OK" if check["ok"] else "FAIL"
        print(f"- {icon} {check['name']}: {check['message']}")

    return 0 if all(check["ok"] for check in checks) else 1


def _check_mt5(settings) -> dict:
    client = MT5Client(
        login=settings.mt5_login,
        password=settings.mt5_password,
        server=settings.mt5_server,
        path=settings.mt5_path,
    )
    try:
        client.connect()
        tick = client.get_tick(settings.mt5_symbol)
        return {
            "name": "MT5",
            "ok": True,
            "message": f"{settings.mt5_symbol} bid={tick.bid}, ask={tick.ask}",
        }
    except Exception as exc:
        return {
            "name": "MT5",
            "ok": False,
            "message": str(exc),
        }
    finally:
        client.shutdown()


def _check_hermes(settings) -> dict:
    if not settings.hermes_api_url:
        return {
            "name": "Hermes",
            "ok": False,
            "message": "HERMES_API_URL is empty.",
        }

    headers = {"Content-Type": "application/json"}
    if settings.hermes_api_key:
        headers["Authorization"] = f"Bearer {settings.hermes_api_key}"

    payload = {
        "model": settings.hermes_model,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "temperature": 0,
    }
    try:
        response = requests.post(
            settings.hermes_api_url,
            json=payload,
            headers=headers,
            timeout=min(settings.hermes_timeout, 15),
        )
        response.raise_for_status()
        return {
            "name": "Hermes",
            "ok": True,
            "message": f"{settings.hermes_model} responded from {settings.hermes_api_url}",
        }
    except Exception as exc:
        return {
            "name": "Hermes",
            "ok": False,
            "message": f"Cannot call Hermes: {exc}",
        }


def _check_feishu(settings) -> dict:
    if settings.feishu_webhook_url:
        return {
            "name": "Feishu",
            "ok": True,
            "message": "FEISHU_WEBHOOK_URL is configured.",
        }
    return {
        "name": "Feishu",
        "ok": False,
        "message": "FEISHU_WEBHOOK_URL is empty. Alerts will only print locally.",
    }


if __name__ == "__main__":
    sys.exit(main())
