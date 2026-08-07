"""Фоновый поток для сетевых и долгих операций (не блокирует GUI)."""

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    """Выполняет функцию в потоке, результат/ошибку шлёт сигналами."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args):
        """Принимает callable и её аргументы для фонового выполнения."""
        super().__init__()
        self.fn, self.args = fn, args

    def run(self):
        """Запускает функцию; исключение превращает в сигнал failed."""
        try:
            self.done.emit(self.fn(*self.args))
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")
