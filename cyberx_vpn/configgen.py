"""Генерация конфигурации sing-box из параметров сервера."""

# Приватные диапазоны НЕ заворачиваются в туннель: локальная сеть
# и docker-мосты (172.16/12) должны остаться доступными напрямую.
ROUTE_EXCLUDE = [
    "10.0.0.0/8",
    "100.64.0.0/10",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "224.0.0.0/4",
]

TUN_IF = "cyberx0"


def build_singbox_config(server: dict) -> dict:
    """Собирает полный конфиг sing-box для TUN-режима под заданный сервер.

    server — словарь из subscription.parse_vless().
    Схема: tun-inbound с auto_route, DNS перехватывается и уходит
    через DoH поверх туннеля, весь остальной трафик — в VLESS+Reality.
    """
    return {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [
                {
                    "tag": "remote",
                    "address": "https://1.1.1.1/dns-query",
                    "detour": "proxy",
                },
            ],
            "final": "remote",
            "strategy": "ipv4_only",
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": TUN_IF,
                "address": ["172.19.0.1/30"],
                "auto_route": True,
                "route_exclude_address": ROUTE_EXCLUDE,
                "sniff": True,
            }
        ],
        "outbounds": [
            {
                "type": "vless",
                "tag": "proxy",
                "server": server["host"],
                "server_port": server["port"],
                "uuid": server["uuid"],
                **({"flow": server["flow"]} if server["flow"] else {}),
                "tls": {
                    "enabled": True,
                    "server_name": server["sni"],
                    "utls": {"enabled": True, "fingerprint": server["fp"]},
                    "reality": {
                        "enabled": True,
                        "public_key": server["pbk"],
                        "short_id": server["sid"],
                    },
                },
            },
            {"type": "direct", "tag": "direct"},
        ],
        "route": {
            # DNS-пакеты, попавшие в туннель, отвечаются локально через dns-модуль
            "rules": [{"protocol": "dns", "action": "hijack-dns"}],
            "final": "proxy",
            "auto_detect_interface": True,
        },
    }
