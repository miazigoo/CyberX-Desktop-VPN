"""Круглая анимированная кнопка подключения (копия ConnectButtonView из Android)."""

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

# период полного оборота анимации (мс) — как в Android-клиенте
ANIM_PERIOD_MS = 1100
TICK_MS = 30


class ConnectButton(QWidget):
    """Большая круглая кнопка GO/ON с градиентом, свечением и дугой прогресса.

    Три состояния: idle (синий градиент, «GO»), connecting (дуга крутится,
    «...»), connected (зелёный градиент, «ON», бирюзовая дуга).
    """

    clicked = Signal()

    def __init__(self, parent=None):
        """Создаёт кнопку 220x220 с таймером анимации."""
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self.setCursor(Qt.PointingHandCursor)
        self._connecting = False
        self._connected = False
        self._value = 0.0  # фаза анимации 0..1
        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    def set_connecting(self, v: bool):
        """Переводит кнопку в/из состояния «подключаемся»."""
        self._connecting = v
        self._sync_anim()

    def set_connected(self, v: bool):
        """Переводит кнопку в/из состояния «подключено»."""
        self._connected = v
        self._sync_anim()

    def _sync_anim(self):
        """Запускает/останавливает таймер анимации по текущему состоянию."""
        if self._connecting or self._connected:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def _tick(self):
        """Продвигает фазу анимации и перерисовывает кнопку."""
        self._value = (self._value + TICK_MS / ANIM_PERIOD_MS) % 1.0
        self.update()

    def mousePressEvent(self, _e):
        """Пробрасывает клик наружу сигналом clicked."""
        self.clicked.emit()

    def paintEvent(self, _e):
        """Рисует кнопку: свечение, градиент, кольца, дугу и подписи."""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        size = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        radius = size * 0.38
        pulse = self._value

        # внешнее бирюзовое свечение, дышащее с фазой анимации
        alpha = int(42 + pulse * 44)
        pen = QPen(QColor(69, 224, 181, alpha))
        pen.setWidthF(size * 0.018)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        glow_r = radius + size * 0.075 + pulse * size * 0.035
        p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

        # основной круг: сине-фиолетовый градиент, в подключении — зелёный
        grad = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        if self._connected:
            grad.setColorAt(0, QColor("#1ED6A5"))
            grad.setColorAt(1, QColor("#0B8F76"))
        else:
            grad.setColorAt(0, QColor("#1677FF"))
            grad.setColorAt(1, QColor("#6D5DFB"))
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        # внутреннее полупрозрачное белое кольцо
        pen = QPen(QColor(255, 255, 255, 130))
        pen.setWidthF(size * 0.034)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        ir = radius - size * 0.025
        p.drawEllipse(QRectF(cx - ir, cy - ir, ir * 2, ir * 2))

        # вращающаяся дуга: белая при подключении, бирюзовая когда подключено
        if self._connecting or self._connected:
            arc_r = radius + size * 0.052
            pen = QPen(QColor("#45E0B5") if self._connected else QColor("#FFFFFF"))
            pen.setWidthF(size * 0.028)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
            p.drawArc(rect, int(self._value * 360 * 16), int(92 * 16))

        # центральная надпись GO/ON/...
        label = "ON" if self._connected else ("..." if self._connecting else "GO")
        f = QFont(self.font())
        f.setPixelSize(int(size * 0.17))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(
            QRectF(0, cy - size * 0.14, self.width(), size * 0.22),
            Qt.AlignHCenter | Qt.AlignVCenter,
            label,
        )

        # подпись-подсказка под центральной надписью
        caption = "TAP TO STOP" if self._connected else "TAP TO CONNECT"
        f2 = QFont(self.font())
        f2.setPixelSize(int(size * 0.06))
        f2.setBold(False)
        p.setFont(f2)
        p.setPen(QColor(236, 245, 255, 210))
        p.drawText(
            QRectF(0, cy + size * 0.12, self.width(), size * 0.12),
            Qt.AlignHCenter | Qt.AlignVCenter,
            caption,
        )
        p.end()
