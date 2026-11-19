"""Главное окно CyberX VPN: серверы подписки, управление туннелем."""

import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..netcheck import check_ip
from ..routing import parse_bypass_list
from ..subscription import fetch_subscription, parse_vless
from ..tunnel import TunManager
from .connect_button import ConnectButton
from .worker import Worker


class MainWindow(QMainWindow):
    """Окно приложения: загрузка подписки, выбор сервера, подключение TUN."""

    def __init__(self, app_dir: str):
        """Строит UI и запускает первичную загрузку подписки."""
        super().__init__()
        self.app_dir = app_dir
        self.settings_file = os.path.join(app_dir, "settings.json")
        logo_48 = os.path.join(app_dir, "assets", "cyberx_mark_48.png")
        logo_256 = os.path.join(app_dir, "assets", "cyberx_mark_256.png")

        self.setWindowTitle("CyberX VPN")
        self.resize(480, 620)
        self._icon = QIcon(logo_256) if os.path.isfile(logo_256) else QIcon()
        if not self._icon.isNull():
            self.setWindowIcon(self._icon)

        # флаг «пользователь вышел из приложения» — отличает выход из трея
        # от простого закрытия окна (которое сворачивает в трей)
        self._quitting = False
        self._tray_hint_shown = False

        self.tun = TunManager(app_dir)
        self.servers: list[dict] = []
        self.current: dict | None = None
        self.connected = False
        self._operation: str | None = None
        self._ip_request = None
        self.settings = self._load_settings()
        self._fetching = False
        self._workers: list = []

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(22, 20, 22, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        if os.path.isfile(logo_48):
            logo = QLabel()
            logo.setPixmap(QPixmap(logo_48))
            head.addWidget(logo)
        brand = QLabel("CyberX VPN")
        brand.setObjectName("brand")
        head.addWidget(brand)
        head.addStretch()
        lay.addLayout(head)

        self.connect_btn = ConnectButton()
        self.connect_btn.clicked.connect(self.on_go_clicked)
        lay.addWidget(self.connect_btn, 0, Qt.AlignCenter)
        self.status_lbl = QLabel("VPN отключён")
        self.status_lbl.setObjectName("status")
        self.status_lbl.setTextFormat(Qt.PlainText)
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status_lbl)

        tabs = QTabWidget()
        lay.addWidget(tabs, 1)
        panel = QWidget()
        panel.setObjectName("page")
        tabs.addTab(panel, "Серверы")
        p_lay = QVBoxLayout(panel)
        p_lay.setContentsMargins(16, 16, 16, 12)
        p_lay.setSpacing(8)

        url_lbl = QLabel("Ссылка подписки")
        url_lbl.setObjectName("panelTitle")
        p_lay.addWidget(url_lbl)
        url_row = QHBoxLayout()
        self.url_edit = QLineEdit(self.settings.get("sub_url", ""))
        self.url_edit.setPlaceholderText("https://…")
        self.url_edit.setAccessibleName(url_lbl.text())
        self.url_edit.returnPressed.connect(self.on_fetch)
        self.url_edit.textChanged.connect(self._subscription_edited)
        self.update_btn = QPushButton("Загрузить")
        self.update_btn.clicked.connect(self.on_fetch)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.update_btn)
        p_lay.addLayout(url_row)

        self.sub_status = QLabel(
            "Введите ссылку от провайдера, чтобы загрузить серверы."
        )
        self.sub_status.setObjectName("hint")
        self.sub_status.setTextFormat(Qt.PlainText)
        self.sub_status.setWordWrap(True)
        p_lay.addWidget(self.sub_status)
        self.list = QListWidget()
        self.list.setAccessibleName("Серверы подписки")
        self.list.currentRowChanged.connect(self._sync_controls)
        self.list.itemActivated.connect(self._connect_selected)
        p_lay.addWidget(self.list, 1)

        exc_panel = QWidget()
        exc_panel.setObjectName("page")
        tabs.addTab(exc_panel, "Исключения")
        exc_lay = QVBoxLayout(exc_panel)
        exc_lay.setContentsMargins(16, 16, 16, 12)
        exc_lay.setSpacing(8)
        self.exclude_lan_cb = QCheckBox("Локальная сеть без VPN")
        self.exclude_lan_cb.setToolTip(
            "192.168.x, 10.x, docker-сети и другие частные адреса идут напрямую"
        )
        self.exclude_lan_cb.setChecked(self.settings.get("exclude_lan", True))
        exc_lay.addWidget(self.exclude_lan_cb)

        bypass_lbl = QLabel("Сайты без VPN (домен, URL или IP — по одному в строке)")
        bypass_lbl.setObjectName("hint")
        bypass_lbl.setWordWrap(True)
        exc_lay.addWidget(bypass_lbl)

        self.bypass_edit = QPlainTextEdit()
        self.bypass_edit.setPlaceholderText("example.com\n192.168.1.10")
        saved_bypass = self.settings.get("bypass", [])
        if isinstance(saved_bypass, list):
            self.bypass_edit.setPlainText("\n".join(saved_bypass))
        else:
            self.bypass_edit.setPlainText(str(saved_bypass))
        self.bypass_edit.setAccessibleName(bypass_lbl.text())
        exc_lay.addWidget(self.bypass_edit)

        exc_hint = QLabel("Применяется при следующем подключении")
        exc_hint.setObjectName("hint")
        exc_lay.addWidget(exc_hint)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setObjectName("log")
        self.log.setAccessibleName("Журнал подключений")
        tabs.addTab(self.log, "Журнал")

        # если туннель остался поднят с прошлого запуска — показываем это
        if self.tun.is_running():
            self.connected = True
            self.status_lbl.setText("Подключено (туннель поднят ранее)")
            self.log_msg("Обнаружен поднятый ранее TUN-интерфейс")
            self._check_ip()

        self._setup_tray()
        self._sync_controls()
        if self.url_edit.text().strip():
            self.on_fetch()
        else:
            self.url_edit.setFocus()

    # --- трей ---

    def _setup_tray(self):
        """Создаёт иконку в системном трее с меню управления.

        Закрытие окна прячет его в трей (туннель продолжает работать),
        полный выход — только через пункт меню «Выход».
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = None
            return
        self.tray = QSystemTrayIcon(self._icon, self)
        menu = QMenu(self)
        self.tray_status_action = menu.addAction("Не подключено")
        self.tray_status_action.setEnabled(False)
        menu.addSeparator()
        open_action = menu.addAction("Открыть")
        open_action.triggered.connect(self._tray_show_window)
        self.tray_toggle_action = menu.addAction("Подключиться")
        self.tray_toggle_action.triggered.connect(self.on_go_clicked)
        menu.addSeparator()
        quit_action = menu.addAction("Выход")
        quit_action.triggered.connect(self._tray_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _sync_controls(self):
        """Обновляет действия окна и трея при смене состояния или сервера."""
        available = self.connected or self.list.currentRow() >= 0
        self.connect_btn.set_state(self.connected, self._operation, available)
        self.update_btn.setEnabled(not self._fetching and not self._operation)
        if not self.tray:
            return
        if self._operation:
            state = self._operation
        elif self.connected:
            name = self.current["name"] if self.current else "туннель"
            state = f"Подключено: {name}"
        else:
            state = "Не подключено"
        self.tray.setToolTip(f"CyberX VPN — {state}")
        self.tray_status_action.setText(state)
        self.tray_toggle_action.setText(
            "Отключиться" if self.connected else "Подключиться"
        )
        self.tray_toggle_action.setEnabled(self.connect_btn.isEnabled())

    def _tray_show_window(self):
        """Показывает и поднимает главное окно из трея."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_activated(self, reason):
        """Клик по иконке трея — показать окно."""
        if reason == QSystemTrayIcon.Trigger:
            self._tray_show_window()

    def _tray_quit(self):
        """Полный выход из приложения (останавливает туннель)."""
        self._quitting = True
        self.close()

    # --- служебное ---

    def _load_settings(self) -> dict:
        """Читает settings.json; при любой проблеме возвращает {}."""
        try:
            with open(self.settings_file, encoding="utf-8") as settings_file:
                settings = json.load(settings_file)
            return settings if isinstance(settings, dict) else {}
        except (OSError, ValueError):
            return {}

    def _routing_settings(self) -> dict:
        """Текущие настройки маршрутизации из UI."""
        return {
            "exclude_lan": self.exclude_lan_cb.isChecked(),
            "bypass": parse_bypass_list(self.bypass_edit.toPlainText()),
        }

    def _save_settings(self):
        """Сохраняет настройки в settings.json."""
        self.settings["sub_url"] = self.url_edit.text().strip()
        self.settings["exclude_lan"] = self.exclude_lan_cb.isChecked()
        self.settings["bypass"] = parse_bypass_list(self.bypass_edit.toPlainText())
        pending = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.app_dir, delete=False, encoding="utf-8"
            ) as temp:
                pending = Path(temp.name)
                json.dump(self.settings, temp, indent=2)
            pending.replace(self.settings_file)
        except OSError as error:
            self.log_msg(f"Не удалось сохранить настройки: {error}")
        finally:
            if pending is not None:
                pending.unlink(missing_ok=True)

    def log_msg(self, msg: str):
        """Добавляет строку в журнал окна."""
        self.log.appendPlainText(msg)

    def _run_worker(self, fn, *args, on_done=None, on_fail=None):
        """Запускает fn в фоне и связывает сигналы с колбэками окна."""
        w = Worker(fn, *args)
        if on_done:
            w.done.connect(on_done)
        w.failed.connect(on_fail or (lambda e: self._err(e)))

        def finished():
            self._workers.remove(w)
            w.deleteLater()
            if self._quitting and not self._workers:
                self.close()

        w.finished.connect(finished)
        self._workers.append(w)
        w.start()

    def _err(self, msg: str):
        """Показывает ошибку в статусе и журнале."""
        self.status_lbl.setText(f"Ошибка: {msg}")
        self.log_msg(f"ОШИБКА: {msg}")

    # --- действия ---

    def _subscription_edited(self, url):
        """Убирает серверы прежней подписки, когда пользователь меняет её адрес."""
        self.list.clear()
        self.servers = []
        if url.strip():
            self.sub_status.setText(
                "Нажмите «Загрузить», чтобы получить список серверов."
            )
        else:
            self.sub_status.setText(
                "Введите ссылку от провайдера, чтобы загрузить серверы."
            )

    def on_fetch(self):
        """Загружает подписку и пересобирает список серверов."""
        if self._operation or self._fetching or self._quitting:
            return
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            self.sub_status.setText(
                "Введите ссылку, начинающуюся с https:// или http://."
            )
            self.url_edit.setFocus()
            return
        self._save_settings()
        self._fetching = True
        self.url_edit.setReadOnly(True)
        self._sync_controls()
        self.sub_status.setText("Загружаем серверы…")

        def load():
            servers = []
            for link in fetch_subscription(url):
                try:
                    servers.append(parse_vless(link))
                except ValueError:
                    continue
            return servers

        def end_fetch():
            self._fetching = False
            self.url_edit.setReadOnly(False)
            self._sync_controls()

        def done(servers):
            row = self.list.currentRow()
            previous = self.servers[row]["raw"] if row >= 0 else None
            self.servers = servers
            self.list.clear()
            selected = 0
            for i, server in enumerate(servers):
                if server["raw"] == previous:
                    selected = i
                name, host, port = server["name"], server["host"], server["port"]
                QListWidgetItem(f"{name}   ·   {host}:{port}", self.list)
            if servers:
                self.list.setCurrentRow(selected)
                message = f"Доступные серверы · {len(servers)}"
            else:
                message = "В подписке нет доступных VLESS-серверов. Проверьте ссылку."
            self.sub_status.setText(message)
            self.log_msg(message)
            end_fetch()

        def fail(error):
            self.sub_status.setText(
                "Не удалось загрузить серверы. Подробнее в журнале."
            )
            self.log_msg(f"Ошибка загрузки подписки: {error}")
            end_fetch()

        self._run_worker(load, on_done=done, on_fail=fail)

    def _connect_selected(self):
        if not self.connected and not self._operation and not self._quitting:
            self._do_connect()

    def on_go_clicked(self):
        """Обрабатывает нажатие кнопки подключения: подключиться или отключиться."""
        if self._operation or self._quitting:
            return
        if self.connected:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        """Запускает подъём TUN к выбранному серверу (в фоне)."""
        row = self.list.currentRow()
        if row < 0 or row >= len(self.servers):
            self.status_lbl.setText("Сначала выберите сервер в списке")
            return
        server = self.servers[row]
        self.current = server
        self._save_settings()
        self._operation = "Подключение…"
        self._sync_controls()
        self.status_lbl.setText(f"Подключение: {server['name']}…")
        self.log_msg(
            f"Поднимаю туннель → {server['name']} ({server['host']}:{server['port']})"
        )
        routing = self._routing_settings()
        self._run_worker(
            self.tun.start,
            server,
            routing,
            on_done=lambda msg: self._tun_up(msg, routing),
            on_fail=self._tun_fail,
        )

    def _tun_up(self, msg, routing):
        """Завершает подключение: зелёная кнопка, проверка внешнего IP."""
        self._operation = None
        self.connected = True
        self._sync_controls()
        self.status_lbl.setText(f"Подключено · {self.current['name']}")
        self.log_msg(f"sing-box: {msg}")
        parts = []
        if routing["exclude_lan"]:
            parts.append("LAN/docker без VPN")
        bypass = routing["bypass"]
        if bypass:
            parts.append(f"обход: {len(bypass)} шт.")
        if parts:
            self.log_msg("Исключения: " + "; ".join(parts))
        else:
            self.log_msg("Весь трафик через туннель (исключений нет)")
        if self._quitting:
            self._do_disconnect()
        else:
            self._check_ip()

    def _check_ip(self):
        """Применяет результат проверки IP только для текущего подключения."""
        request = object()
        self._ip_request = request

        def done(info):
            if self._ip_request is request:
                name = self.current["name"] if self.current else "туннель"
                self.status_lbl.setText(f"{name}  ·  IP: {info}")
                self.log_msg(f"Внешний IP через VPN: {info}")

        def fail(error):
            if self._ip_request is request:
                self.log_msg(f"Не удалось проверить внешний IP: {error}")

        self._run_worker(check_ip, on_done=done, on_fail=fail)

    def _tun_fail(self, e):
        """Откатывает UI в исходное состояние при неудачном подключении."""
        self._operation = None
        self.connected = False
        self.current = None
        self._sync_controls()
        self._err(e)

    def _do_disconnect(self):
        """Останавливает туннель в фоне, пока пользователь отвечает на запрос polkit."""
        self._ip_request = None
        self._operation = "Отключение…"
        self._sync_controls()
        self.status_lbl.setText(self._operation)

        def done(msg):
            self._operation = None
            self.connected = False
            self.current = None
            self._sync_controls()
            self.status_lbl.setText("VPN отключён")
            self.log_msg(f"sing-box: {msg}; маршруты и DNS восстановлены")

        def fail(error):
            self._operation = None
            if self._quitting:
                self._quitting = False
                self.setEnabled(True)
                self._tray_show_window()
            self._sync_controls()
            self.status_lbl.setText("Не удалось отключить VPN. Подробнее в журнале.")
            self.log_msg(f"Ошибка отключения: {error}")

        self._run_worker(self.tun.stop, on_done=done, on_fail=fail)

    def closeEvent(self, event):
        """Сворачивает окно в трей или завершает фоновые задачи и останавливает VPN."""
        self._save_settings()
        if self.tray and not self._quitting:
            event.ignore()
            self.hide()
            if not self._tray_hint_shown:
                self._tray_hint_shown = True
                self.tray.showMessage(
                    "CyberX VPN",
                    "Открыть приложение и выйти можно через меню значка.",
                    self._icon,
                    4000,
                )
            return
        self._quitting = True
        if self.connected and not self._operation:
            self._do_disconnect()
        if self._workers:
            self.setEnabled(False)
            if not self._operation:
                self.status_lbl.setText("Завершаем текущую операцию…")
            event.ignore()
            return
        event.accept()
        QApplication.instance().quit()
