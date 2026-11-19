"""Тесты ядра: парсинг vless и генерация конфига sing-box (без GUI и сети)."""

import base64
from io import BytesIO

import pytest

from cyberx_vpn.configgen import (
    ROUTE_EXCLUDE,
    TUN_IF,
    build_singbox_config,
)
from cyberx_vpn.routing import build_bypass_route_rule, parse_bypass_list
from cyberx_vpn.subscription import fetch_subscription, parse_vless

VLESS = (
    "vless://00000000-0000-4000-8000-000000000001@192.0.2.1:443"
    "?security=reality&type=tcp&flow=xtls-rprx-vision&sni=example.org&fp=chrome"
    "&pbk=AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA&sid=aabbccdd"
    "#%D0%A2%D0%B5%D1%81%D1%82"
)


def test_parse_vless_fields():
    """Все ключевые поля vless-ссылки извлекаются корректно."""
    s = parse_vless(VLESS)
    assert s["host"] == "192.0.2.1"
    assert s["port"] == 443
    assert s["uuid"] == "00000000-0000-4000-8000-000000000001"
    assert s["security"] == "reality"
    assert s["sni"] == "example.org"
    assert s["flow"] == "xtls-rprx-vision"
    assert s["name"] == "Тест"


def test_singbox_config_structure():
    """Конфиг sing-box содержит tun-inbound, reality и DNS-перехват."""
    cfg = build_singbox_config(parse_vless(VLESS))

    tun = cfg["inbounds"][0]
    assert tun["type"] == "tun"
    assert tun["interface_name"] == TUN_IF
    assert tun["auto_route"] is True
    assert tun["route_exclude_address"] == ROUTE_EXCLUDE

    out = cfg["outbounds"][0]
    assert out["type"] == "vless"
    assert out["server"] == "192.0.2.1"
    assert out["tls"]["reality"]["public_key"].startswith("AQIDBAUG")
    assert out["tls"]["server_name"] == "example.org"

    assert {"protocol": "dns", "action": "hijack-dns"} in cfg["route"]["rules"]
    assert len(cfg["dns"]["servers"]) == 2


def test_singbox_no_lan_exclude():
    """Без exclude_lan приватные сети не исключаются из TUN."""
    cfg = build_singbox_config(parse_vless(VLESS), exclude_lan=False)
    tun = cfg["inbounds"][0]
    assert "route_exclude_address" not in tun


def test_singbox_bypass_domains():
    """Домены из списка обхода идут через direct."""
    cfg = build_singbox_config(
        parse_vless(VLESS),
        bypass=["youtube.com", "2ip.ru", "10.1.2.3"],
    )
    rules = cfg["route"]["rules"]
    bypass = next(r for r in rules if r.get("outbound") == "direct")
    assert "youtube.com" in bypass["domain_suffix"]
    assert "2ip.ru" in bypass["domain_suffix"]
    assert "10.1.2.3/32" in bypass["ip_cidr"]
    assert cfg["dns"]["rules"]


def test_singbox_bypass_uses_network_dns():
    """Исключённые внутренние домены резолвятся DNS текущей сети."""
    cfg = build_singbox_config(
        parse_vless(VLESS),
        bypass=["srv-dnp.argos.loc"],
        direct_dns="172.16.2.5",
    )
    direct_dns = next(s for s in cfg["dns"]["servers"] if s["tag"] == "direct")
    assert direct_dns["address"] == "172.16.2.5"


def test_parse_bypass_list():
    """Список обхода парсится из текста с комментариями."""
    items = parse_bypass_list("ya.ru\n# skip\n\n*.google.com, github.com")
    assert items == ["ya.ru", "*.google.com", "github.com"]


def test_bypass_url_is_normalized_to_domain():
    """URL из адресной строки браузера применяется к домену и поддоменам."""
    rule = build_bypass_route_rule(["https://srv-dnp.argos.loc/path?q=1"])
    assert rule == {"outbound": "direct", "domain_suffix": ["srv-dnp.argos.loc"]}


def test_build_bypass_route_rule():
    """Правило обхода собирается только из валидных записей."""
    rule = build_bypass_route_rule(["bad domain!", "ok.ru"])
    assert rule == {"outbound": "direct", "domain_suffix": ["ok.ru"]}


@pytest.mark.parametrize("encoded", [False, True])
def test_fetch_subscription_decodes_server_list(monkeypatch, encoded):
    body = f"{VLESS}\n{VLESS}\n".encode()
    response = base64.b64encode(body).rstrip(b"=") if encoded else body
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: BytesIO(response))
    assert fetch_subscription("https://example.org/sub") == [VLESS, VLESS]


@pytest.mark.parametrize(
    "link", ["vless://host", "vless://user@:443", "vless://user@host:invalid"]
)
def test_parse_vless_rejects_incomplete_server(link):
    with pytest.raises(ValueError):
        parse_vless(link)
