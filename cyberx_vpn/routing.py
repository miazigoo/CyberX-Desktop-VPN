"""Правила маршрутизации: исключение LAN и обход VPN для выбранных сайтов."""

import ipaddress
import re
from urllib.parse import urlsplit

# Приватные диапазоны не заворачиваются в TUN, когда включено «LAN без VPN».
LAN_EXCLUDE = [
    "10.0.0.0/8",
    "100.64.0.0/10",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "224.0.0.0/4",
]

_DOMAIN_LABEL = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$",
    re.IGNORECASE,
)


def parse_bypass_list(raw: str | list[str] | None) -> list[str]:
    """Разбирает список исключений из текста или массива."""
    if raw is None:
        return []
    if isinstance(raw, list):
        lines = raw
    else:
        lines = raw.replace(",", "\n").splitlines()
    out: list[str] = []
    for line in lines:
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        out.append(item)
    return out


def _is_ip_or_cidr(value: str) -> bool:
    if "/" in value:
        try:
            ipaddress.ip_network(value, strict=False)
            return True
        except ValueError:
            return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def classify_bypass_entry(entry: str) -> tuple[str, str]:
    """Возвращает ('ip_cidr'|'domain'|'domain_suffix', normalized_value)."""
    value = entry.strip().lower()
    if not value:
        raise ValueError("пустая запись")

    # Пользователь часто вставляет адрес из строки браузера.  Для правила нужен
    # только хост: путь, порт, схема и query-параметры к маршрутизации не имеют
    # отношения.  urlsplit без схемы считает домен путём, поэтому разбираем URL
    # только когда схема явно указана.
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError(f"некорректный URL: {entry}")
        value = parsed.hostname.lower()

    if _is_ip_or_cidr(value):
        if "/" not in value:
            return "ip_cidr", f"{value}/32"
        net = ipaddress.ip_network(value, strict=False)
        return "ip_cidr", str(net)

    if value.startswith("*."):
        domain = value[2:]
    elif value.startswith("."):
        domain = value[1:]
    else:
        domain = value

    domain = domain.strip(".")
    if not domain or not _DOMAIN_LABEL.fullmatch(domain):
        raise ValueError(f"некорректный домен: {entry}")

    # Начиная с sing-box 1.9 значение БЕЗ точки покрывает и сам домен, и его
    # поддомены. Значение с точкой не совпадает с корневым доменом (например,
    # `.youtube.com` не ловит `youtube.com`), из-за чего исключения выглядели
    # рабочими, но не применялись к основному сайту.
    return "domain_suffix", domain


def build_bypass_route_rule(entries: list[str]) -> dict | None:
    """Собирает sing-box route rule для трафика мимо VPN."""
    suffixes: list[str] = []
    cidrs: list[str] = []

    for entry in entries:
        try:
            kind, norm = classify_bypass_entry(entry)
        except ValueError:
            continue
        if kind == "ip_cidr":
            cidrs.append(norm)
        elif kind == "domain_suffix" and norm not in suffixes:
            suffixes.append(norm)

    if not suffixes and not cidrs:
        return None

    rule: dict = {"outbound": "direct"}
    if suffixes:
        rule["domain_suffix"] = suffixes
    if cidrs:
        rule["ip_cidr"] = cidrs
    return rule


def build_bypass_dns_rules(entries: list[str]) -> list[dict]:
    """DNS-запросы для обходимых доменов резолвятся напрямую."""
    suffixes: list[str] = []
    for entry in entries:
        try:
            kind, norm = classify_bypass_entry(entry)
        except ValueError:
            continue
        if kind == "domain_suffix" and norm not in suffixes:
            suffixes.append(norm)

    if not suffixes:
        return []
    return [{"domain_suffix": suffixes, "server": "direct"}]
