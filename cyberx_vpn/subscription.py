"""Загрузка подписки и разбор vless:// ссылок."""

import base64
import binascii
import urllib.parse
import urllib.request


def fetch_subscription(url: str) -> list[str]:
    """Скачивает подписку по URL и возвращает список vless:// ссылок.

    Тело ответа — base64 со списком ссылок построчно; если декодирование
    не удалось, пробуем читать тело как plain text.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Happ/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read().strip()

    text = raw.decode("utf-8-sig", errors="replace")
    if not any(line.strip().startswith("vless://") for line in text.splitlines()):
        token = b"".join(raw.split())
        try:
            decoded = base64.b64decode(
                token + b"=" * (-len(token) % 4), altchars=b"-_", validate=True
            )
            text = decoded.decode("utf-8-sig")
        except (binascii.Error, UnicodeDecodeError):
            return []
    return [ln.strip() for ln in text.splitlines() if ln.strip().startswith("vless://")]


def parse_vless(link: str) -> dict:
    """Разбирает vless:// ссылку в словарь параметров сервера.

    Возвращает dict с ключами: name, host, port, uuid, flow, type,
    security, sni, fp, pbk, sid, raw.
    """
    u = urllib.parse.urlparse(link)
    if u.scheme != "vless" or not u.hostname or not u.username:
        raise ValueError("В ссылке VLESS отсутствует адрес сервера или идентификатор.")
    port = 443 if u.port is None else u.port
    if port == 0:
        raise ValueError("Неверный порт в ссылке VLESS.")
    q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
    return {
        "name": urllib.parse.unquote(u.fragment) or f"{u.hostname}:{port}",
        "host": u.hostname,
        "port": port,
        "uuid": u.username,
        "flow": q.get("flow", ""),
        "type": q.get("type", "tcp"),
        "security": q.get("security", ""),
        "sni": q.get("sni", ""),
        "fp": q.get("fp", "chrome"),
        "pbk": q.get("pbk", ""),
        "sid": q.get("sid", ""),
        "raw": link,
    }
