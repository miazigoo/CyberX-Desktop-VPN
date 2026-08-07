"""QSS-стиль приложения в фирменной тёмной теме CyberX (как Android-клиент)."""

STYLE = """
QMainWindow, QWidget {
    background: #0B1220;
    color: #E7F0FF;
    font-family: "Inter", "Segoe UI", "Noto Sans", sans-serif;
    font-size: 14px;
}
QLabel#brand {
    font-size: 30px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel#tagline { color: #8EA4C8; font-size: 13px; }
QLabel#panelTitle { color: #8EA4C8; font-size: 13px; }
QLabel#status { color: #E7F0FF; font-size: 15px; }
QLabel#hint { color: #7F94B6; font-size: 12px; }
QFrame#glass {
    background: rgba(16, 24, 39, 0.80);
    border: 1px solid rgba(69, 224, 181, 0.20);
    border-radius: 18px;
}
QLineEdit {
    background: rgba(19, 29, 46, 0.55);
    border: 1px solid rgba(95, 123, 168, 0.25);
    border-radius: 12px;
    padding: 9px 12px;
    color: #FFFFFF;
    selection-background-color: #1677FF;
}
QLineEdit:focus { border: 1px solid #1677FF; }
QPushButton {
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(95, 123, 168, 0.25);
    border-radius: 12px;
    padding: 9px 16px;
    color: #E7F0FF;
    font-weight: 600;
}
QPushButton:hover { background: rgba(255, 255, 255, 0.16); }
QPushButton:pressed { background: rgba(255, 255, 255, 0.07); }
QPushButton:disabled { color: #4A5B76; background: rgba(255,255,255,0.04); }
QPushButton#refreshBtn { font-size: 18px; padding: 6px 12px; border-radius: 12px; }
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(95, 123, 168, 0.18);
    border-radius: 10px;
    padding: 11px 12px;
    margin: 3px 0px;
    color: #E7F0FF;
}
QListWidget::item:hover { background: rgba(255, 255, 255, 0.10); }
QListWidget::item:selected {
    background: rgba(22, 119, 255, 0.28);
    border: 1px solid #1677FF;
    color: #FFFFFF;
}
QPlainTextEdit {
    background: #070D18;
    border: 1px solid #16233A;
    border-radius: 10px;
    color: #5F7394;
    font-family: "JetBrains Mono", "DejaVu Sans Mono", monospace;
    font-size: 11px;
    padding: 6px;
}
QToolTip { background: #131D2E; color: #E7F0FF; border: 1px solid #335F7BA8; }
"""
