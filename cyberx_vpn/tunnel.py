"""Управление TUN-туннелем (sing-box) и привилегированными операциями."""

import ipaddress
import json
import os
import subprocess

from .configgen import TUN_IF, build_singbox_config


class TunManager:
    """Запускает и останавливает sing-box TUN через helper.sh от root.

    GUI работает от пользователя, а подъём интерфейса, маршруты и
    подмена /etc/resolv.conf требуют root — они вынесены в helper.sh.
    После `tools/install.sh` вызывается через passwordless sudo;
    без установки — fallback на pkexec (polkit-запрос пароля).
    """

    def __init__(self, app_dir: str):
        """Запоминает пути до sing-box, helper.sh и каталога runtime."""
        self.singbox_bin = os.path.join(app_dir, "sing-box")
        self.helper = os.path.realpath(os.path.join(app_dir, "helper.sh"))
        self.runtime_dir = os.path.join(app_dir, "runtime")

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

    def _run_helper(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def _helper(self, action: str) -> str:
        """Вызывает helper.sh от root, возвращает его stdout."""
        r = self._run_helper(["sudo", "-n", self.helper, action])
        if r.returncode == 0:
            return r.stdout.strip()

        err = (r.stderr or r.stdout or "").lower()
        if "password" in err or "a password is required" in err:
            r = self._run_helper(["pkexec", self.helper, action])
            if r.returncode == 126:
                raise RuntimeError("pkexec: запрос прав отменён или нет polkit-агента")
            if r.returncode != 0:
                raise RuntimeError(
                    r.stderr.strip()
                    or r.stdout.strip()
                    or f"helper {action}: код {r.returncode}"
                )
            return r.stdout.strip()

        raise RuntimeError(
            r.stderr.strip()
            or r.stdout.strip()
            or f"helper {action}: код {r.returncode}"
        )

    @staticmethod
    def _current_dns_server() -> str | None:
        """Возвращает первый IP DNS из resolv.conf до подъёма TUN."""
        try:
            with open("/etc/resolv.conf", encoding="utf-8") as resolv_conf:
                for line in resolv_conf:
                    fields = line.split()
                    if len(fields) == 2 and fields[0] == "nameserver":
                        try:
                            return str(ipaddress.ip_address(fields[1]))
                        except ValueError:
                            continue
        except OSError:
            pass
        return None

    def start(self, server: dict, routing: dict | None = None) -> str:
        """Пишет конфиг sing-box и поднимает туннель через helper."""
        routing = routing or {}
        os.makedirs(self.runtime_dir, exist_ok=True)
        cfg_path = os.path.join(self.runtime_dir, "singbox.json")
        direct_dns = self._current_dns_server()
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(
                build_singbox_config(
                    server,
                    exclude_lan=routing.get("exclude_lan", True),
                    bypass=routing.get("bypass", []),
                    direct_dns=direct_dns,
                ),
                f,
                indent=2,
            )
        return self._helper("up")

    def stop(self) -> str:
        """Останавливает туннель и восстанавливает resolv.conf через helper."""
        if self.is_running():
            return self._helper("down")
        return "DOWN"
