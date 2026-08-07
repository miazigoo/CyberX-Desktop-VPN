"""Главное окно CyberX VPN: список серверов, кнопка GO, управление туннелем."""

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..netcheck import check_ip
from ..subscription import fetch_subscription, parse_vless
from ..tunnel import TunManager
from .connect_button import ConnectButton
from .worker import Worker

DEFAULT_SUB_URL = "https://sub.cyberx-net.org/sub/Rm9yX1Bhc2hhLDE3ODMzMjk1NjIzw7t7mjugn"


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
        self.resize(480, 760)
        if os.path.isfile(logo_256):
            self.setWindowIcon(QIcon(logo_256))

        self.tun = TunManager(app_dir)
        self.servers: list[dict] = []
        self.current: dict | None = None
        self.connected = False
        self.connecting = False
        self.settings = self._load_settings()
        self._workers: list = []

        root = QWidget()
        self.setCentralWidget(root)
        lay = QVBoxLayout(root)
        lay.setContentsMargins(22, 20, 22, 14)
        lay.setSpacing(10)

        # шапка: логотип + бренд + кнопка обновления подписки
        head = QHBoxLayout()
        if os.path.isfile(logo_48):
            logo = QLabel()
            logo.setPixmap(QPixmap(logo_48))
            head.addWidget(logo)
        brand_box = QVBoxLayout()
        brand_box.setSpacing(0)
        brand = QLabel("CyberX")
        brand.setObjectName("brand")
        tagline = QLabel("Private network access")
        tagline.setObjectName("tagline")
        brand_box.addWidget(brand)
        brand_box.addWidget(tagline)
        head.addLayout(brand_box, 1)
        self.fetch_btn = QPushButton("⟳")
        self.fetch_btn.setObjectName("refreshBtn")
        self.fetch_btn.setToolTip("Обновить подписку")
        self.fetch_btn.clicked.connect(self.on_fetch)
        head.addWidget(self.fetch_btn, 0, Qt.AlignVCenter)
        lay.addLayout(head)

        lay.addSpacing(6)

        # круглая кнопка подключения по центру
        btn_row = QHBoxLayout()
        self.connect_btn = ConnectButton()
        self.connect_btn.clicked.connect(self.on_go_clicked)
        btn_row.addStretch(1)
        btn_row.addWidget(self.connect_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        self.status_lbl = QLabel("Загрузка серверов...")
        self.status_lbl.setObjectName("status")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.status_lbl)

        # «стеклянная» панель со списком серверов и ссылкой подписки
        panel = QFrame()
        panel.setObjectName("glass")
        p_lay = QVBoxLayout(panel)
        p_lay.setContentsMargins(16, 14, 16, 14)
        p_lay.setSpacing(8)
        p_title = QLabel("Маршрут подключения")
        p_title.setObjectName("panelTitle")
        p_lay.addWidget(p_title)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _i: self.on_go_clicked())
        p_lay.addWidget(self.list, 1)

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_edit = QLineEdit(self.settings.get("sub_url", DEFAULT_SUB_URL))
        self.url_edit.setPlaceholderText("Ссылка подписки https://...")
        self.update_btn = QPushButton("Обновить")
        self.update_btn.clicked.connect(self.on_fetch)
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(self.update_btn)
        p_lay.addLayout(url_row)

        hint = QLabel("Выберите сервер в списке и нажмите GO")
        hint.setObjectName("hint")
        hint.setAlignment(Qt.AlignCenter)
        p_lay.addWidget(hint)
        lay.addWidget(panel, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setFixedHeight(84)
        lay.addWidget(self.log)

        # если туннель остался поднят с прошлого запуска — показываем это
        if self.tun.is_running():
            self.connected = True
            self.connect_btn.set_connected(True)
            self.status_lbl.setText("Подключено (туннель поднят ранее)")
            self.log_msg("Обнаружен поднятый ранее TUN-интерфейс")
            self._run_worker(check_ip, on_done=self._ip_ok, on_fail=lambda e: None)
        self.on_fetch()

    # --- служебное ---

    def _load_settings(self) -> dict:
        """Читает settings.json; при любой проблеме возвращает {}."""
        try:
            return json.load(open(self.settings_file, encoding="utf-8"))
        except Exception:
            return {}

    def _save_settings(self):
        """Сохраняет ссылку подписки в settings.json."""
        self.settings["sub_url"] = self.url_edit.text().strip()
        try:
            json.dump(
                self.settings,
                open(self.settings_file, "w", encoding="utf-8"),
                indent=2,
            )
        except Exception:
            pass

    def log_msg(self, msg: str):
        """Добавляет строку в журнал окна."""
        self.log.appendPlainText(msg)

    def _run_worker(self, fn, *args, on_done=None, on_fail=None):
        """Запускает fn в фоне и связывает сигналы с колбэками окна."""
        w = Worker(fn, *args)
        if on_done:
            w.done.connect(on_done)
        w.failed.connect(on_fail or (lambda e: self._err(e)))
        w.finished.connect(lambda: self._workers.remove(w))
        self._workers.append(w)
        w.start()

    def _err(self, msg: str):
        """Показывает ошибку в статусе и журнале."""
        self.status_lbl.setText(f"Ошибка: {msg}")
        self.log_msg(f"ОШИБКА: {msg}")

    # --- действия ---

    def on_fetch(self):
        """Загружает подписку и пересобирает список серверов."""
        if self.connecting:
            return
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "CyberX VPN", "Нужна http/https ссылка подписки")
            return
        self._save_settings()
        self.fetch_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.status_lbl.setText("Загружаю серверы...")

        def done(links):
            self.fetch_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
            self.servers = [parse_vless(ln) for ln in links]
            self.list.clear()
            for s in self.servers:
                QListWidgetItem(
                    f"{s['name']}    ·    {s['host']}:{s['port']}", self.list
                )
            if self.list.count():
                self.list.setCurrentRow(0)
            if not self.connected:
                self.status_lbl.setText(
                    f"Серверов: {len(self.servers)}. Готов к подключению"
                )
            self.log_msg(f"Подписка загружена, серверов: {len(self.servers)}")

        def fail(e):
            self.fetch_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
            self._err(e)

        self._run_worker(fetch_subscription, url, on_done=done, on_fail=fail)

    def on_go_clicked(self):
        """Обрабатывает нажатие GO/ON: подключиться или отключиться."""
        if self.connecting:
            return
        if self.connected:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        """Запускает подъём TUN к выбранному серверу (в фоне, через pkexec)."""
        row = self.list.currentRow()
        if row < 0 or row >= len(self.servers):
            self.status_lbl.setText("Сначала выберите сервер в списке")
            return
        server = self.servers[row]
        self.current = server
        self._save_settings()
        self.connecting = True
        self.connect_btn.set_connecting(True)
        self.status_lbl.setText(f"Подключение: {server['name']} (запрос пароля)")
        self.log_msg(
            f"Поднимаю туннель → {server['name']} ({server['host']}:{server['port']})"
        )
        self._run_worker(
            lambda: self.tun.start(server),
            on_done=self._tun_up,
            on_fail=self._tun_fail,
        )

    def _tun_up(self, msg):
        """Завершает подключение: зелёная кнопка, проверка внешнего IP."""
        self.connecting = False
        self.connected = True
        self.connect_btn.set_connecting(False)
        self.connect_btn.set_connected(True)
        self.log_msg(f"sing-box: {msg}")
        self.log_msg(
            "Весь трафик через туннель; DNS → DoH через VPN; "
            "LAN и docker-сети исключены."
        )
        self._run_worker(
            check_ip,
            on_done=self._ip_ok,
            on_fail=lambda e: self._err(f"Туннель поднят, но трафик не идёт: {e}"),
        )

    def _tun_fail(self, e):
        """Откатывает UI в исходное состояние при неудачном подключении."""
        self.connecting = False
        self.connected = False
        self.connect_btn.set_connecting(False)
        self._err(e)

    def _ip_ok(self, info):
        """Показывает внешний IP, полученный через туннель."""
        name = self.current["name"] if self.current else "туннель"
        self.status_lbl.setText(f"{name}  ·  IP: {info}")
        self.log_msg(f"Внешний IP через VPN: {info}")

    def _do_disconnect(self):
        """Останавливает туннель и возвращает UI в состояние «отключено»."""
        try:
            msg = self.tun.stop()
            self.log_msg(f"sing-box: {msg}; маршруты и DNS восстановлены")
        except Exception as e:
            self._err(str(e))
        self.connected = False
        self.current = None
        self.connect_btn.set_connected(False)
        self.status_lbl.setText("Не подключено. Готов к подключению")

    def closeEvent(self, event):
        """При закрытии сохраняет настройки и аккуратно гасит туннель."""
        self._save_settings()
        if self.connected:
            try:
                self.tun.stop()
            except Exception:
                pass
        event.accept()
