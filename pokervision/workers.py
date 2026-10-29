"""Executor Qt de uma tarefa por vez, com cancelamento e sinais para a GUI."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from .resources import CancelToken, Cancelled


class Signals(QObject):
    progress = Signal(object)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class Task(QRunnable):
    def __init__(self, operation, token):
        super().__init__()
        self.operation, self.token, self.signals = operation, token, Signals()

    @Slot()
    def run(self):
        try:
            result = self.operation(self.token, self.signals.progress.emit)
            self.token.check()
            self.signals.result.emit(result)
        except Cancelled:
            self.signals.error.emit('Solicitação cancelada. O simulador continua funcionando.')
        except Exception as exc:
            self.signals.error.emit(str(exc))
        finally:
            self.signals.finished.emit()


class BackgroundJobs(QObject):
    busy_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self.task = None

    @property
    def busy(self):
        return self.task is not None

    def start(self, operation, result, error, progress=None):
        if self.busy:
            return False
        task = Task(operation, CancelToken())
        self.task = task
        task.signals.result.connect(result)
        task.signals.error.connect(error)
        if progress:
            task.signals.progress.connect(progress)
        task.signals.finished.connect(self._finished)
        self.busy_changed.emit(True)
        self.pool.start(task)
        return True

    @Slot()
    def _finished(self):
        self.task = None
        self.busy_changed.emit(False)

    def cancel(self):
        if self.task:
            self.task.token.cancel()
