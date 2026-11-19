"""Управление TUN-туннелем (sing-box) и привилегированными операциями."""

import ipaddress
import json
import os
import subprocess

from .configgen import TUN_IF, build_singbox_config


class TunManager:
    """Управляет TUN через установленный системный помощник и polkit."""

    def __init__(self, app_dir: str):
        """Принимает каталог GUI для совместимости с существующими клиентами."""
        self.helper = "/usr/local/lib/cyberx-vpn/helper.sh"

    def is_running(self) -> bool:
        """Проверяет, поднят ли TUN-интерфейс (признак активного туннеля)."""
        try:
            r = subprocess.run(
                ["ip", "link", "show", TUN_IF],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _helper(self, action: str, config: dict | None = None) -> str:
        """Запрашивает авторизацию polkit и передаёт конфигурацию через stdin."""
        if not os.access(self.helper, os.X_OK):
            raise RuntimeError(
                "Системный помощник не установлен. Запустите ./tools/install.sh."
            )
        try:
            result = subprocess.run(
                ["/usr/bin/pkexec", "--disable-internal-agent", self.helper, action],
                input=json.dumps(config) if config is not None else "",
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Для управления VPN установите пакет pkexec.") from exc
        if result.returncode == 126:
            raise RuntimeError("Запрос прав администратора отменён.")
        if result.returncode == 127:
            raise RuntimeError(
                "Ubuntu не выдала права. Запустите CyberX VPN из графического сеанса "
                "и подтвердите запрос администратора."
            )
        if result.returncode:
            raise RuntimeError(
                result.stderr.strip() or f"Ошибка {action}: {result.returncode}"
            )
        return result.stdout.strip()

    @staticmethod
    def _current_dns_server() -> str | None:
        """Возвращает первый IP DNS из resolv.conf до подъёма TUN."""
        for path in ("/etc/resolv.conf", "/run/systemd/resolve/resolv.conf"):
            try:
                with open(path, encoding="utf-8") as resolv_conf:
                    for line in resolv_conf:
                        fields = line.split()
                        if len(fields) < 2 or fields[0] != "nameserver":
                            continue
                        try:
                            address = str(ipaddress.ip_address(fields[1]))
                        except ValueError:
                            continue
                        # resolved направит запрос, посланный локальному stub, в VPN.
                        if address not in {"127.0.0.53", "127.0.0.54"}:
                            return address
            except OSError:
                continue
        return None

    def start(self, server: dict, routing: dict | None = None) -> str:
        """Передаёт конфигурацию помощнику и поднимает туннель."""
        routing = routing or {}
        config = build_singbox_config(
            server,
            exclude_lan=routing.get("exclude_lan", True),
            bypass=routing.get("bypass", []),
            direct_dns=self._current_dns_server(),
        )
        return self._helper("up", config)

    def stop(self) -> str:
        """Останавливает туннель и освобождает настройки DNS."""
        return self._helper("down")
