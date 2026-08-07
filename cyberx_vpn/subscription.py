"""Загрузка подписки и разбор vless:// ссылок."""

import base64
import urllib.parse
import urllib.request


def fetch_subscription(url: str) -> list[str]:
    """Скачивает подписку по URL и возвращает список vless:// ссылок.

    Тело ответа — base64 со списком ссылок построчно; если декодирование
    не удалось, пробуем читать тело как plain text.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "Happ/1.0"})
    raw = urllib.request.urlopen(req, timeout=20).read().strip()
    try:
        # дополняем padding, токены в подписках его часто не имеют
        text = base64.b64decode(raw + b"=" * (-len(raw) % 4)).decode("utf-8", "replace")
    except Exception:
        text = raw.decode("utf-8", "replace")
    return [ln.strip() for ln in text.splitlines() if ln.strip().startswith("vless://")]


def parse_vless(link: str) -> dict:
    """Разбирает vless:// ссылку в словарь параметров сервера.

    Возвращает dict с ключами: name, host, port, uuid, flow, type,
    security, sni, fp, pbk, sid, raw.
    """
    u = urllib.parse.urlparse(link)
    q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
    return {
        "name": urllib.parse.unquote(u.fragment) or f"{u.hostname}:{u.port}",
        "host": u.hostname,
        "port": u.port or 443,
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
