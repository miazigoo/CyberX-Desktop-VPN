"""Тесты ядра: парсинг vless и генерация конфига sing-box (без GUI и сети)."""

import base64

from cyberx_vpn.configgen import (
    ROUTE_EXCLUDE,
    TUN_IF,
    build_singbox_config,
)
from cyberx_vpn.routing import build_bypass_route_rule, parse_bypass_list
from cyberx_vpn.subscription import parse_vless

VLESS = (
    "vless://c3804846-fcf9-438d-a22f-934629b27bd2@144.31.186.100:443"
    "?security=reality&type=tcp&flow=xtls-rprx-vision&sni=ya.ru&fp=chrome"
    "&pbk=XyXna691nvnWIbwvwPbYMDNZ__5GVfQKU_kc8IPoGTI&sid=a3f8c1d2"
    "#%D0%A2%D0%B5%D1%81%D1%82"
)


def test_parse_vless_fields():
    """Все ключевые поля vless-ссылки извлекаются корректно."""
    s = parse_vless(VLESS)
    assert s["host"] == "144.31.186.100"
    assert s["port"] == 443
    assert s["uuid"] == "c3804846-fcf9-438d-a22f-934629b27bd2"
    assert s["security"] == "reality"
    assert s["sni"] == "ya.ru"
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
    assert out["server"] == "144.31.186.100"
    assert out["tls"]["reality"]["public_key"].startswith("XyXna691")
    assert out["tls"]["server_name"] == "ya.ru"

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


def test_subscription_body_decoding():
    """base64-тело подписки без padding декодируется в список ссылок."""
    body = "\n".join([VLESS, VLESS]).encode()
    tok = base64.b64encode(body).rstrip(b"=")
    raw = tok + b"=" * (-len(tok) % 4)
    text = base64.b64decode(raw).decode()
    links = [ln for ln in text.splitlines() if ln.startswith("vless://")]
    assert len(links) == 2
