"""Генерация конфигурации sing-box из параметров сервера."""

from .routing import (
    LAN_EXCLUDE,
    build_bypass_dns_rules,
    build_bypass_route_rule,
    parse_bypass_list,
)

# Обратная совместимость для тестов и внешних импортов.
ROUTE_EXCLUDE = LAN_EXCLUDE

TUN_IF = "cyberx0"


def build_singbox_config(
    server: dict,
    *,
    exclude_lan: bool = True,
    bypass: list[str] | str | None = None,
    direct_dns: str | None = None,
) -> dict:
    """Собирает полный конфиг sing-box для TUN-режима под заданный сервер.

    server — словарь из subscription.parse_vless().
    exclude_lan — не направлять приватные подсети в туннель.
    bypass — домены/IP, которые идут напрямую, минуя VPN.
    direct_dns — DNS-сервер текущей сети для исключённых доменов.
    """
    bypass_entries = parse_bypass_list(bypass)
    bypass_rule = build_bypass_route_rule(bypass_entries)
    bypass_dns = build_bypass_dns_rules(bypass_entries)

    tun_inbound: dict = {
        "type": "tun",
        "tag": "tun-in",
        "interface_name": TUN_IF,
        "address": ["172.19.0.1/30"],
        "auto_route": True,
        "sniff": True,
    }
    if exclude_lan:
        tun_inbound["route_exclude_address"] = LAN_EXCLUDE

    dns_servers = [
        {
            "tag": "remote",
            "address": "https://1.1.1.1/dns-query",
            "detour": "proxy",
        },
        {
            "tag": "direct",
            # Внутренние имена (например, *.corp или *.loc) доступны только
            # через DNS текущей сети, а не через публичный резолвер.
            "address": direct_dns or "223.5.5.5",
            "detour": "direct",
        },
    ]

    route_rules: list[dict] = [{"protocol": "dns", "action": "hijack-dns"}]
    if bypass_rule:
        route_rules.append(bypass_rule)

    dns_block: dict = {
        "servers": dns_servers,
        "rules": bypass_dns,
        "final": "remote",
        "strategy": "ipv4_only",
    }

    return {
        "log": {"level": "info", "timestamp": True},
        "dns": dns_block,
        "inbounds": [tun_inbound],
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
            "rules": route_rules,
            "final": "proxy",
            "auto_detect_interface": True,
        },
    }
