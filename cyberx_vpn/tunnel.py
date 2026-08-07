"""Управление TUN-туннелем (sing-box) и привилегированными операциями."""

import json
import os
import subprocess

from .configgen import TUN_IF, build_singbox_config


class TunManager:
    """Запускает и останавливает sing-box TUN через pkexec helper.sh.

    GUI работает от пользователя, а подъём интерфейса, маршруты и
    подмена /etc/resolv.conf требуют root — они вынесены в helper.sh,
    вызываемый через pkexec (polkit покажет запрос пароля).
    """

    def __init__(self, app_dir: str):
        """Запоминает пути до sing-box, helper.sh и каталога runtime."""
        self.singbox_bin = os.path.join(app_dir, "sing-box")
        self.helper = os.path.join(app_dir, "helper.sh")
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

    def _helper(self, action: str) -> str:
        """Вызывает helper.sh от root через pkexec, возвращает его stdout."""
        r = subprocess.run(
            ["pkexec", self.helper, action],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        # 126 у pkexec — пользователь отменил запрос или нет polkit-агента
        if r.returncode == 126:
            raise RuntimeError("pkexec: запрос прав отменён или нет polkit-агента")
        if r.returncode != 0:
            raise RuntimeError(
                r.stderr.strip()
                or r.stdout.strip()
                or f"helper {action}: код {r.returncode}"
            )
        return r.stdout.strip()

    def start(self, server: dict) -> str:
        """Пишет конфиг sing-box и поднимает туннель через helper."""
        os.makedirs(self.runtime_dir, exist_ok=True)
        cfg_path = os.path.join(self.runtime_dir, "singbox.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(build_singbox_config(server), f, indent=2)
        return self._helper("up")

    def stop(self) -> str:
        """Останавливает туннель и восстанавливает resolv.conf через helper."""
        if self.is_running():
            return self._helper("down")
        return "DOWN"
