"""Точка входа приложения CyberX VPN."""

import os
import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow
from .ui.style import STYLE


def _app_dir() -> str:
    """Определяет каталог приложения: рядом с exe (бандл) или с исходниками."""
    if getattr(sys, "frozen", False):
        # PyInstaller-бандл: ресурсы лежат рядом с исполняемым файлом
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    """Создаёт QApplication, применяет тему и показывает главное окно."""
    app = QApplication(sys.argv)
    app.setApplicationName("CyberX VPN")
    app.setStyleSheet(STYLE)
    # окно сворачивается в трей, а не закрывает приложение
    app.setQuitOnLastWindowClosed(False)
    w = MainWindow(_app_dir())
    w.show()
    sys.exit(app.exec())
