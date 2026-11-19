"""Круглая кнопка подключения с индикатором состояния VPN."""

from PySide6.QtCore import QLineF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton


class ConnectButton(QAbstractButton):
    """Кнопка с символом питания и дугой ожидания при подключении."""

    def __init__(self, parent=None):
        """Создаёт кнопку с поддержкой фокуса и нажатия пробелом."""
        super().__init__(parent)
        self.setFixedSize(176, 176)
        self.setFocusPolicy(Qt.StrongFocus)
        self._busy = False
        self._connected = False
        self._angle = 0
        self._timer = QTimer(self, interval=40)
        self._timer.timeout.connect(self._tick)
        self.set_state(False, None, False)

    def set_state(self, connected: bool, operation: str | None, available: bool):
        """Синхронизирует подпись, доступность и анимацию с состоянием туннеля."""
        self._connected = connected
        self._busy = bool(operation)
        if operation:
            self.setText(operation)
            self._timer.start()
        else:
            self.setText("Отключиться" if connected else "Подключиться")
            self._timer.stop()
        self.setEnabled(available and not operation)
        self.setCursor(Qt.PointingHandCursor if self.isEnabled() else Qt.ArrowCursor)
        self.update()

    def _tick(self):
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, _event):
        """Рисует символ питания, подпись и кольцо клавиатурного фокуса."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        circle = QRectF(12, 12, 152, 152)
        gradient = QLinearGradient(circle.topLeft(), circle.bottomRight())
        if self._connected:
            start, end = "#167E6A", "#07564C"
        elif self.isEnabled() or self._busy:
            start, end = "#236BE1", "#4D47BD"
        else:
            start, end = "#2C3C56", "#1A273C"
        gradient.setColorAt(0, QColor(start))
        gradient.setColorAt(1, QColor(end))
        p.setBrush(gradient)
        p.setPen(QPen(QColor(start).lighter(150), 2))
        p.drawEllipse(circle)

        p.setBrush(Qt.NoBrush)
        pen = QPen(QColor("#F5F9FF"), 4, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(68, 54, 40, 40), 125 * 16, 290 * 16)
        p.drawLine(QLineF(88, 49, 88, 72))

        font = self.font()
        font.setPixelSize(14)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRectF(16, 102, 144, 28), Qt.AlignCenter, self.text())

        ring = circle.adjusted(-6, -6, 6, 6)
        if self._busy:
            p.setPen(QPen(QColor("#86B6FF"), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(ring, -self._angle * 16, 95 * 16)
        elif self.hasFocus():
            p.setPen(QPen(QColor("#B4CCFF"), 2))
            p.drawEllipse(ring)
        p.end()
