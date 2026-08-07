"""Тесты ядра: парсинг vless и генерация конфига sing-box (без GUI и сети)."""

import base64

from cyberx_vpn.configgen import ROUTE_EXCLUDE, TUN_IF, build_singbox_config
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


def test_subscription_body_decoding():
    """base64-тело подписки без padding декодируется в список ссылок."""
    body = "\n".join([VLESS, VLESS]).encode()
    tok = base64.b64encode(body).rstrip(b"=")
    raw = tok + b"=" * (-len(tok) % 4)
    text = base64.b64decode(raw).decode()
    links = [ln for ln in text.splitlines() if ln.startswith("vless://")]
    assert len(links) == 2
