import threading
import time

import pytest

qt_widgets = pytest.importorskip("PySide6.QtWidgets")


def wait_until(condition):
    deadline = time.monotonic() + 5
    while not condition() and time.monotonic() < deadline:
        qt_widgets.QApplication.processEvents()
        time.sleep(0.005)
    assert condition()


@pytest.fixture
def window(tmp_path, monkeypatch):
    from cyberx_vpn.ui.main_window import MainWindow, TunManager

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(
        qt_widgets.QSystemTrayIcon, "isSystemTrayAvailable", lambda: False
    )
    monkeypatch.setattr(TunManager, "is_running", lambda _self: False)
    monkeypatch.setattr(TunManager, "start", lambda _self, server, routing: "UP")
    monkeypatch.setattr(TunManager, "stop", lambda _self: "DOWN")
    app = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    w = MainWindow(str(tmp_path))
    w.show()
    yield w
    wait_until(lambda: not w._workers)
    w.hide()
    w.deleteLater()
    app.processEvents()


def load_servers(window, monkeypatch):
    def fetch(_url):
        uuid = "11111111-2222-4333-8444-555555555555"
        return [
            f"vless://{uuid}@one.example.org:443?security=reality#First",
            f"vless://{uuid}@two.example.org:443?security=reality#Second",
        ]

    monkeypatch.setattr("cyberx_vpn.ui.main_window.fetch_subscription", fetch)
    window.url_edit.setText("https://example.org/subscription")
    window.update_btn.click()
    wait_until(lambda: not window._workers)
    assert window.list.count() == 2


def test_changed_subscription_cannot_connect_to_old_server(window, monkeypatch):
    assert not window.url_edit.text()
    assert not window._workers
    assert not window.connect_btn.isEnabled()
    load_servers(window, monkeypatch)
    assert window.connect_btn.isEnabled()

    def offline(_url):
        raise OSError("offline")

    monkeypatch.setattr("cyberx_vpn.ui.main_window.fetch_subscription", offline)
    window.url_edit.setText("https://example.org/new-subscription")
    assert not window.list.count()
    assert not window.connect_btn.isEnabled()
    window.update_btn.click()
    wait_until(lambda: not window._workers)
    assert not window.servers
    assert "Не удалось" in window.sub_status.text()


def test_old_ip_check_cannot_replace_new_connection_status(window, monkeypatch):
    load_servers(window, monkeypatch)
    first_check = threading.Event()
    release_first = threading.Event()

    def check_ip():
        if first_check.is_set():
            return "203.0.113.2"
        first_check.set()
        release_first.wait(5)
        return "203.0.113.1"

    monkeypatch.setattr("cyberx_vpn.ui.main_window.check_ip", check_ip)
    window.connect_btn.click()
    try:
        wait_until(first_check.is_set)
        window.connect_btn.click()
        wait_until(lambda: not window.connected)
        window.list.setCurrentRow(1)
        window.connect_btn.click()
        wait_until(lambda: "203.0.113.2" in window.status_lbl.text())
    finally:
        release_first.set()
    wait_until(lambda: not window._workers)
    assert "Second" in window.status_lbl.text()
    assert "203.0.113.2" in window.status_lbl.text()


@pytest.mark.parametrize("from_tray", [False, True])
def test_cancel_quit_during_polkit_then_retry(window, monkeypatch, from_tray):
    window.connected = True
    window._sync_controls()
    release = threading.Event()
    called = threading.Event()

    def cancel():
        assert threading.current_thread() is not threading.main_thread()
        called.set()
        release.wait(5)
        raise RuntimeError("Запрос прав администратора отменён.")

    monkeypatch.setattr(window.tun, "stop", cancel)
    window.connect_btn.click()
    try:
        wait_until(called.is_set)
        if from_tray:
            window.hide()
            window._tray_quit()
        else:
            assert not window.close()
        assert window.connect_btn.text() == "Отключение…"
        assert not window.connect_btn.isEnabled()
    finally:
        release.set()
    wait_until(lambda: not window._workers)
    assert window.isVisible() and window.connected and window.connect_btn.isEnabled()
    assert "отменён" in window.log.toPlainText()
    monkeypatch.setattr(window.tun, "stop", lambda: "DOWN")
    window.close()
    wait_until(lambda: not window._workers)
    assert not window.connected and not window.isVisible()
