"""Проверка внешнего IP (для подтверждения, что туннель работает)."""

import json
import urllib.request


def check_ip() -> str:
    """Возвращает внешний IP и гео строкой вида «1.2.3.4 — Frankfurt, DE».

    В TUN-режиме запрос сам уходит через туннель, поэтому успешный ответ
    подтверждает, что трафик маршрутизируется через VPN.
    """
    req = urllib.request.Request(
        "https://ipinfo.io/json", headers={"User-Agent": "curl/8"}
    )
    d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    return f"{d.get('ip', '?')} — {d.get('city', '')}, {d.get('country', '')}"
