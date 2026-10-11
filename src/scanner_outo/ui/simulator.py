"""Processo Qt pertencente a esta janela; controlo HTTP fora da thread grafica."""

from __future__ import annotations

import http.client
import importlib.util
import json
import os
import secrets
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QProcess, QProcessEnvironment, QThreadPool, QTimer, Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, QSpinBox, QLabel, QPushButton, QStyle

from scanner_outo.config import PROJECT_ROOT
from scanner_outo.ui.workers import Worker
from scanner_outo.ui.components import Panel, Columns, TechnicalSection
from scanner_outo.ui.design import icon as design_icon

SCENARIOS = ("healthy", "rough_idle_p0301", "multiple_dtcs", "no_data", "connection_loss", "car")
SCENARIO_NAMES = ("Motor saudável", "Ralenti irregular | P0301", "Múltiplas avarias", "ECU sem dados", "Perda de ligação", "Veículo original (car)")


class SimulatorPanel(QWidget):
    before_change = Signal(str)
    changed = Signal()
    stopped = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_error)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.child_handle = None
        self.kernel = None
        if os.name == "nt":
            self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            self.kernel.OpenProcess.restype = wintypes.HANDLE
            self.kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
            self.kernel.TerminateProcess.restype = wintypes.BOOL
            self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            self.kernel.CloseHandle.restype = wintypes.BOOL
        self.control_port = None
        self.token = ""
        self.buffer = ""
        self.stderr = ""
        self.ready = False
        self.busy = False
        self.stopping = False
        self.transition = False
        self.vehicle = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.workers = []
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.timeout.connect(self.expired)
        layout = QVBoxLayout(self)
        self.setObjectName("page")
        layout.setContentsMargins(24, 0, 24, 24)
        layout.setSpacing(24)
        scenario_panel = Panel("Cenários de teste disponíveis")
        state_panel = Panel("Estado interno do simulador")
        form = QFormLayout()
        self.scenario = QComboBox()
        for name, identifier in zip(SCENARIO_NAMES, SCENARIOS):
            self.scenario.addItem(name, identifier)
        self.scenario.setCurrentIndex(self.scenario.findData("rough_idle_p0301"))
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(35000)
        self.loss_count = QSpinBox()
        self.loss_count.setRange(1, 100000)
        self.loss_count.setValue(12)
        form.addRow("Cenário", self.scenario)
        form.addRow("Endereço", QLabel("127.0.0.1"))
        form.addRow("Porta OBD", self.port)
        form.addRow("Pedidos OBD antes da perda", self.loss_count)
        scenario_panel.body.addLayout(form)
        def button(text, callback, icon):
            symbol = {QStyle.StandardPixmap.SP_MediaPlay: "play_arrow", QStyle.StandardPixmap.SP_MediaStop: "stop",
                      QStyle.StandardPixmap.SP_BrowserReload: "refresh", QStyle.StandardPixmap.SP_DialogApplyButton: "check_circle"}.get(icon, "science")
            item = QPushButton(design_icon(symbol), text)
            item.setToolTip(text)
            item.clicked.connect(callback)
            return item
        icons = QStyle.StandardPixmap
        self.start_button = button("Iniciar simulador", self.start, icons.SP_MediaPlay)
        self.stop_button = button("Parar simulador", lambda: self.before_change.emit("stop"), icons.SP_MediaStop)
        scenario_panel.body.addWidget(Columns([self.start_button, self.stop_button], breakpoint=440))
        self.cycle_button = button("Novo ciclo", lambda: self.request("cycle"), icons.SP_ArrowForward)
        self.resolve_button = button("Resolver causa", lambda: self.request("resolve"), icons.SP_DialogApplyButton)
        self.reset_button = button("Repor cenário", lambda: self.before_change.emit("reset"), icons.SP_BrowserReload)
        self.status_button = button("Actualizar estado", lambda: self.request("status"), icons.SP_BrowserReload)
        self.start_button.setToolTip("Iniciar simulador não liga automaticamente o scanner.")
        self.cycle_button.setToolTip("Novo ciclo exige nova consulta OBD para actualizar a tabela de avarias.")
        self.resolve_button.setToolTip("Resolver causa não elimina os códigos já guardados.")
        scenario_panel.body.addWidget(Columns([self.cycle_button, self.resolve_button, self.reset_button, self.status_button], breakpoint=440, maximum=4))
        self.start_button.setProperty("variant", "primary")
        self.start_button.setIcon(design_icon("play_arrow", "#FFFFFF"))
        self.stop_button.setProperty("variant", "danger")
        self.process_status = QLabel("Parado; nenhum processo gerido")
        self.process_status.setWordWrap(True)
        self.vehicle_status = QLabel("Estado do veículo não consultado")
        self.vehicle_status.setWordWrap(True)
        state_panel.body.addWidget(self.vehicle_status)
        self.process_status.setProperty("role", "technical")
        state_panel.body.addWidget(TechnicalSection("Processo e portas locais", self.process_status))
        state_panel.body.addStretch()
        layout.addWidget(Columns([scenario_panel, state_panel], breakpoint=1100))
        layout.addStretch()
        self.update_controls()

    @property
    def owned(self):
        return self.process.state() != QProcess.ProcessState.NotRunning

    def update_controls(self):
        free = not self.owned and not self.busy and not self.transition
        self.start_button.setEnabled(free)
        self.stop_button.setEnabled(self.owned and not self.stopping and not self.transition)
        for field in (self.scenario, self.port, self.loss_count):
            field.setEnabled(free)
        controls = self.ready and self.owned and not self.busy and not self.stopping and not self.transition
        self.reset_button.setEnabled(controls)
        self.status_button.setEnabled(controls)
        for button in (self.cycle_button, self.resolve_button):
            button.setEnabled(controls and self.scenario.currentData() not in ("car", "no_data"))

    def start(self):
        if self.owned or self.busy:
            return
        path = PROJECT_ROOT / "scripts/emulator_environment.py"
        if not path.is_file():
            self.process_status.setText("Launcher não encontrado neste checkout.")
            return
        spec = importlib.util.spec_from_file_location("emulator_environment", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        try:
            interpreter = module.find_emulator_python()
        except FileNotFoundError:
            interpreter = None
        if interpreter is None:
            self.process_status.setText("Ambiente do emulador não encontrado. Verifique ELM327_PYTHON ou simulador_scanner/.venv.")
            return
        self.ready = False
        self.stopping = False
        self.control_port = None
        self.buffer = self.stderr = ""
        self.vehicle = None
        self.token = secrets.token_hex(24)
        environment = QProcessEnvironment.systemEnvironment()
        for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
            environment.remove(key)
        environment.insert("SCANNER_CONTROL_TOKEN", self.token)
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(PROJECT_ROOT))
        self.process.setProgram(str(interpreter))
        self.process.setArguments(["-X", "utf8", "-u", str(PROJECT_ROOT / "scripts/run_fault_emulator.py"),
                                   "--scenario", self.scenario.currentData(), "--port", str(self.port.value()),
                                   "--loss-after-requests", str(self.loss_count.value())])
        self.process_status.setText(f"A iniciar processo gerido em 127.0.0.1:{self.port.value()}…")
        self.process.start()
        self.deadline.start(10000)
        self.update_controls()
        self.changed.emit()

    def read_error(self):
        self.stderr = (self.stderr + bytes(self.process.readAllStandardError()).decode("utf-8", "replace"))[-8192:]

    def read_output(self):
        self.buffer += bytes(self.process.readAllStandardOutput()).decode("utf-8", "replace")
        if len(self.buffer) > 32768:
            self.process_status.setText("Saída do launcher inválida.")
            self.stop()
            return
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if not line.startswith("CONTROL "):
                continue
            try:
                info = json.loads(line[8:])
                port = info["port"]
                if type(port) is not int or not 1 <= port <= 65535 or info["token"] != self.token or self.process.processId() not in (info["pid"], info.get("parent_pid")) or info["scenario"] != self.scenario.currentData():
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                self.process_status.setText("Identificação do processo inválida.")
                self.stop()
                return
            self.control_port = port
            if self.kernel and info["pid"] != self.process.processId():
                # O handle fica fixado enquanto o filho autenticado ainda corre;
                # nunca se volta a procurar pelo PID, que poderia ser reutilizado.
                self.child_handle = self.kernel.OpenProcess(0x0001, False, info["pid"])
                if not self.child_handle:
                    self.process_status.setText("Sem permissão para gerir o processo filho; a encerrar pelo controlo.")
                    self.ready = True
                    self.stop()
                    return
            self.ready = True
            if not self.stopping:
                self.deadline.stop()
            self.process_status.setText(f"Simulador em execução | {self.scenario.currentText()} | 127.0.0.1:{self.port.value()}")
            self.process_status.setToolTip(f"PID {info['pid']} | Controlo local: 127.0.0.1:{port}")
            self.request("shutdown" if self.stopping else "status")
            self.changed.emit()

    def request(self, action, done=None):
        if not self.ready or self.busy or not self.owned:
            return False
        port, token = self.control_port, self.token
        self.busy = True
        def operation():
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
            try:
                connection.request("POST", "/control", json.dumps({"action": action}),
                                   {"Authorization": "Bearer " + token, "Content-Type": "application/json"})
                response = connection.getresponse()
                if response.status != 200:
                    return {"ok": False}
                result = json.loads(response.read(8192))
                if not isinstance(result, dict) or result.get("ok") is not True or not isinstance(result.get("state"), dict):
                    return {"ok": False}
                return result
            except (OSError, ValueError, http.client.HTTPException):
                return {"ok": False}
            finally:
                connection.close()
        worker = Worker(operation)
        self.workers.append(worker)
        def received(result):
            if token != self.token:
                return
            if not result.get("ok"):
                self.vehicle_status.setText("Falha no canal de controlo local.")
                return
            self.vehicle = result["state"]
            value = self.vehicle
            if value["scenario"] == "car":
                self.vehicle_status.setText("Cenário original car; estado interno do veículo não modelado por este painel.")
                if done:
                    done()
                return
            if value["scenario"] == "no_data":
                self.vehicle_status.setText("Adaptador funcional; ECU indisponível (NO DATA).")
                if done:
                    done()
                return
            monitors = ", ".join("Falhas de combustão: " + ("concluído" if status == "complete" else "incompleto")
                                 for status in value["monitors"].values()) or "nenhum"
            self.vehicle_status.setText(
                f"Causa: {'activa' if value['active_causes'] else 'resolvida/ausente'} · MIL: {'acesa' if value['mil'] else 'apagada'}\n"
                f"Confirmados: {', '.join(value['confirmed']) or 'nenhum'} · Pendentes: {', '.join(value['pending']) or 'nenhum'}\n"
                f"Ciclos: {value['cycles']} · Monitores modelados: {monitors} · Pedidos OBD: {value['obd_requests']}"
            )
            if done:
                done()
        def finished():
            self.workers.remove(worker)
            self.busy = False
            self.update_controls()
        worker.signals.succeeded.connect(received, Qt.ConnectionType.QueuedConnection)
        worker.signals.finished.connect(finished, Qt.ConnectionType.QueuedConnection)
        self.pool.start(worker)
        self.update_controls()
        return True

    def stop(self):
        if not self.owned or self.stopping:
            return
        self.stopping = True
        # Apenas o QProcess desta janela; nunca procura nem termina outros PIDs.
        self.shutdown_request()
        self.deadline.start(5000)
        self.update_controls()

    def shutdown_request(self):
        if not self.owned or not self.ready:
            return
        if self.busy:
            QTimer.singleShot(30, self.shutdown_request)
        else:
            self.request("shutdown")

    def expired(self):
        if self.owned:
            self.process_status.setText("Timeout do processo gerido; a encerrar.")
            if self.child_handle:
                self.kernel.TerminateProcess(self.child_handle, 1)
            self.process.kill()

    def process_error(self, _error):
        if not self.owned:
            self.deadline.stop()
            self.process_status.setText("Não foi possível iniciar o Python do emulador.")
            self.update_controls()
            self.stopped.emit(False)

    def finished(self, code, _status):
        if self.child_handle:
            # Tambem impede um filho abandonado caso o redirector termine sozinho.
            self.kernel.TerminateProcess(self.child_handle, 1)
            self.kernel.CloseHandle(self.child_handle)
            self.child_handle = None
        self.read_error()
        was_ready = self.ready
        self.ready = False
        self.deadline.stop()
        self.control_port = None
        detail = "Parado; nenhum processo gerido"
        if code and not self.stopping:
            detail = ("Porta ocupada/indisponível; servidor externo preservado." if "ocupada/indisponivel" in self.stderr
                      else "Falha ao iniciar o emulador. Verifique o ambiente e a versão 4.0.0.")
        self.process_status.setText(detail)
        self.vehicle_status.setText("Estado do veículo desactualizado; processo parado")
        self.stopping = False
        self.update_controls()
        self.changed.emit()
        self.stopped.emit(was_ready)
