from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from scanner_outo.communication.base import TransportError
from scanner_outo.diagnostics.obd import ObdDecodeError
from scanner_outo.services import OperationCancelled
from scanner_outo.gemini import AnalysisError
from scanner_outo.persistence import StorageError


class WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class Worker(QRunnable):
    def __init__(self, operation: Callable) -> None:
        super().__init__()
        self.operation = operation
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.succeeded.emit(self.operation())
        except (TransportError, ObdDecodeError, OperationCancelled, AnalysisError, StorageError) as exc:
            self.signals.failed.emit(str(exc))
        except Exception:
            self.signals.failed.emit("Operacao falhou. Verifique a ligacao ou o acesso aos ficheiros.")
        finally:
            self.signals.finished.emit()
