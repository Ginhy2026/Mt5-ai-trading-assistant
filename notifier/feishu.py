from __future__ import annotations

import base64
import hashlib
import hmac
import time

import requests


class FeishuNotifier:
    def __init__(self, webhook_url: str | None, secret: str | None = None, timeout: int = 20) -> None:
        self.webhook_url = webhook_url
        self.secret = secret
        self.timeout = timeout

    def send_markdown_report(self, report: str) -> None:
        if not self.webhook_url:
            print("FEISHU_WEBHOOK_URL is not configured. Report was not sent.")
            print(report)
            return

        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": "MT5 AI Trading Assistant"},
                    "template": "blue",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": report,
                        },
                    }
                ],
            },
        }
        if self.secret:
            timestamp = str(int(time.time()))
            payload["timestamp"] = timestamp
            payload["sign"] = _build_signature(timestamp, self.secret)

        response = requests.post(self.webhook_url, json=payload, timeout=self.timeout)
        response.raise_for_status()


def _build_signature(timestamp: str, secret: str) -> str:
    string_to_sign = f"{timestamp}\n{secret}".encode("utf-8")
    digest = hmac.new(string_to_sign, b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")
