"""Тёмная тема CyberX для десктопного клиента."""

STYLE = """
QMainWindow, QWidget {
    background: #0B1220;
    color: #E7F0FF;
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 14px;
}
QLabel, QCheckBox { background: transparent; }
QLabel#brand { font-size: 26px; font-weight: 700; color: white; }
QLabel#panelTitle { color: #E7F0FF; font-size: 14px; font-weight: 600; }
QLabel#status { color: #E7F0FF; font-size: 15px; font-weight: 600; }
QLabel#hint { color: #A4B6D1; font-size: 13px; }
QTabWidget::pane {
    background: #101B2D;
    border: none;
    border-top: 1px solid #32425D;
}
QWidget#page { background: #101B2D; }
QTabBar::tab {
    background: transparent;
    color: #ADBCD3;
    padding: 9px 15px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected { color: white; border-bottom-color: #70ABFF; }
QTabBar::tab:hover { color: white; }
QLineEdit, QPlainTextEdit {
    background: #0C1524;
    border: 1px solid #40516B;
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #2165BE;
}
QLineEdit:focus, QPlainTextEdit:focus, QPushButton:focus, QListWidget:focus {
    border: 1px solid #80B2FF;
}
QPushButton {
    background: #29466C;
    border: 1px solid #426590;
    border-radius: 8px;
    padding: 8px 14px;
    color: white;
    font-weight: 600;
}
QPushButton:hover { background: #365A89; }
QPushButton:pressed { background: #203857; }
QPushButton:disabled { color: #9CAFC9; background: #213048; border-color: #304059; }
QListWidget { background: transparent; border: 1px solid transparent; }
QListWidget::item {
    background: #18263B;
    border: 1px solid #2A3B54;
    border-radius: 8px;
    padding: 9px 10px;
    margin: 2px 0;
}
QListWidget::item:hover { background: #20334F; }
QListWidget::item:selected { background: #1D3960; border-color: #629BF1; color: white; }
QScrollBar:vertical { width: 8px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #4B5D77; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QPlainTextEdit#log {
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 12px;
    color: #B6C9E6;
}
QCheckBox { spacing: 8px; }
QToolTip { background: #131D2E; color: #E7F0FF; border: 1px solid #40516B; }
"""
