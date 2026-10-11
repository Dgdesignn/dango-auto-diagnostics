from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPlainTextEdit, QMessageBox, QFileDialog, QDialog, QStyle, QApplication, QMenu,
)

from scanner_outo.config import Settings
from scanner_outo.communication.serial_transport import available_ports
from scanner_outo.models import (
    ConnectionConfig, origin_label, session_origin, OriginError, QUERYING, AVAILABLE, STALE,
)
from scanner_outo.services import DiagnosticService
from scanner_outo.persistence import SessionStore
from scanner_outo.gemini import GeminiService, analysis_payload, analysis_fingerprint, AnalysisError, ANALYSIS_LABELS
from scanner_outo.diagnostics.obd import PIDS, DEFAULT_PIDS
from scanner_outo.diagnostics.timeseries import ReadingSeries
from scanner_outo.ui.charts import ReadingChart
from scanner_outo.ui.workers import Worker
from scanner_outo.ui.theme import apply_theme, STYLESHEET
from scanner_outo.ui.simulator import SimulatorPanel
from scanner_outo.models import Session


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        apply_theme(QApplication.instance())
        self.settings = settings or Settings.load()
        self.store = SessionStore(self.settings.data_dir / "sessions.sqlite3")
        self.service = DiagnosticService()
        self.gemini = GeminiService(self.settings, self.store)
        self.state = self.service.session.to_dict()
        self.pools = {key: QThreadPool(self) for key in ("diag", "other")}
        for pool in self.pools.values():
            pool.setMaxThreadCount(1)
        self.busy = {"diag": False, "other": False}
        self.workers: list[Worker] = []
        self.closing = False
        self.disconnect_pending = False
        self.last_error = ""
        self.history_rows: list[dict] = []
        self.readings_paused = False
        self.series = ReadingSeries()
        self.last_analysis = None
        self.last_analysis_input = None
        self.last_analysis_session = None
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.age_timer = QTimer(self)
        self.age_timer.timeout.connect(self.render_readings)
        self.setWindowTitle("Scanner Outo | Diagnóstico automóvel")
        self.resize(1120, 740)
        self.setMinimumSize(860, 600)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 16, 20, 16)
        heading = QLabel("Scanner Outo")
        heading.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(heading)
        self.connection_status = QLabel()
        self.connection_status.setWordWrap(True)
        layout.addWidget(self.connection_status)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._connection_tab()
        self._data_tab()
        self._codes_tab()
        self._ai_tab()
        self._history_tab()
        self.simulator = SimulatorPanel(self)
        self.tabs.addTab(self.simulator, "Simulador local")
        self.simulator.before_change.connect(self.change_simulator)
        self.simulator.changed.connect(self.render_connection)
        self.simulator.stopped.connect(self.simulator_stopped)
        self.setStyleSheet(STYLESHEET)
        self.apply_state(self.state)
        self.refresh_history()
        self.age_timer.start(1000)

    def page(self, title: str):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.tabs.addTab(page, title)
        return layout

    def button(self, text: str, callback: Callable, icon=QStyle.StandardPixmap.SP_ArrowForward) -> QPushButton:
        button = QPushButton(self.style().standardIcon(icon), text)
        button.setToolTip(text)
        button.clicked.connect(callback)
        return button

    def table(self, columns: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _connection_tab(self) -> None:
        layout = self.page("Ligação")
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(["TCP", "Serial USB", "Bluetooth SPP"])
        self.origin = QComboBox()
        self.origin.addItem(origin_label(True), True)
        self.origin.addItem(origin_label(False), False)
        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(35000)
        self.serial_port = QComboBox()
        self.serial_port.setEditable(True)
        self.serial_port.addItems(available_ports())
        serial_row = QWidget()
        serial_layout = QHBoxLayout(serial_row)
        serial_layout.setContentsMargins(0, 0, 0, 0)
        serial_layout.addWidget(self.serial_port)
        self.scan_ports = self.button("Actualizar", self.rescan_ports, QStyle.StandardPixmap.SP_BrowserReload)
        self.scan_ports.setToolTip("Actualizar portas COM")
        serial_layout.addWidget(self.scan_ports)
        self.baud = QComboBox()
        self.baud.addItems(["9600", "38400", "57600", "115200"])
        self.baud.setCurrentText("38400")
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(1, 10)
        self.timeout.setValue(4)
        self.timeout.setSuffix(" s")
        for label, widget in (("Tipo", self.kind), ("Origem", self.origin), ("Host TCP", self.host), ("Porta TCP", self.port), ("Porta COM / Bluetooth SPP", serial_row), ("Baud rate", self.baud), ("Timeout por pedido", self.timeout)):
            form.addRow(label, widget)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        self.connect_button = self.button("Ligar", self.connect_adapter, QStyle.StandardPixmap.SP_DialogApplyButton)
        self.disconnect_button = self.button("Desligar", self.disconnect_adapter, QStyle.StandardPixmap.SP_DialogCancelButton)
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.disconnect_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addStretch()
        self.kind.currentTextChanged.connect(self.update_controls)

    def _data_tab(self) -> None:
        layout = self.page("Dados")
        row = QHBoxLayout()
        self.read_button = self.button("Actualizar", self.poll, QStyle.StandardPixmap.SP_BrowserReload)
        self.start_button = self.button("Iniciar actualização", self.start_polling, QStyle.StandardPixmap.SP_MediaPlay)
        self.stop_button = self.button("Parar", self.stop_polling, QStyle.StandardPixmap.SP_MediaStop)
        self.interval = QSpinBox()
        self.interval.setRange(2, 60)
        self.interval.setValue(3)
        self.interval.setSuffix(" s")
        self.interval.valueChanged.connect(lambda value: self.poll_timer.setInterval(value * 1000))
        for widget in (self.read_button, self.start_button, self.stop_button, QLabel("Intervalo"), self.interval):
            row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)
        selection = QHBoxLayout()
        self.pid_button = self.button("Parâmetros", lambda: None)
        menu = QMenu(self.pid_button)
        menu.addAction("Seleccionar todos", lambda: self.set_selected_pids(PIDS))
        menu.addAction("Selecção inicial", lambda: self.set_selected_pids(DEFAULT_PIDS))
        menu.addSeparator()
        self.pid_actions = {}
        for pid, definition in PIDS.items():
            action = QAction(f"{pid:02X} | {definition.name} ({definition.unit})", menu)
            action.setCheckable(True)
            action.setChecked(pid in DEFAULT_PIDS)
            action.toggled.connect(self.selection_changed)
            menu.addAction(action)
            self.pid_actions[pid] = action
        self.pid_button.setMenu(menu)
        selection.addWidget(self.pid_button)
        self.selection_label = QLabel()
        selection.addWidget(self.selection_label)
        selection.addStretch()
        layout.addLayout(selection)
        self.data_table = self.table(["Parâmetro", "ECU", "Valor", "Unidade", "Leitura (local)", "Disponibilidade", "Detalhe"])
        self.data_views = QTabWidget()
        self.data_views.addTab(self.data_table, "Leituras")
        self.reading_chart = ReadingChart(self.series)
        self.data_views.addTab(self.reading_chart, "Gráfico")
        layout.addWidget(self.data_views, 1)
        self.support_label = QLabel()
        self.support_label.setWordWrap(True)
        layout.addWidget(self.support_label)
        self.stop_button.setToolTip("Parar consultas conserva os pontos e não encerra o simulador.")
        self.selection_changed()

    def selected_pids(self) -> tuple[int, ...]:
        return tuple(pid for pid, action in self.pid_actions.items() if action.isChecked())

    def set_selected_pids(self, pids) -> None:
        for pid, action in self.pid_actions.items():
            action.blockSignals(True)
            action.setChecked(pid in pids)
            action.blockSignals(False)
        self.selection_changed()

    def selection_changed(self, *_):
        selected = self.selected_pids()
        self.series.interrupt([f"{pid:02X}" for pid in PIDS if pid not in selected])
        self.selection_label.setText(f"{len(selected)} / {len(PIDS)} seleccionados")
        if hasattr(self, "reading_chart"):
            self.reading_chart.select_pids(selected)

    def _codes_tab(self) -> None:
        layout = self.page("Avarias")
        row = QHBoxLayout()
        self.codes_button = self.button("Consultar avarias", self.read_codes, QStyle.StandardPixmap.SP_BrowserReload)
        self.freeze_button = self.button("Consultar freeze frame", self.read_freeze)
        self.clear_button = self.button("Limpar registos", self.prepare_clear, QStyle.StandardPixmap.SP_TrashIcon)
        for button in (self.codes_button, self.freeze_button, self.clear_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.codes_status = QLabel("Não consultado")
        self.codes_status.setWordWrap(True)
        layout.addWidget(self.codes_status)
        self.codes_table = self.table(["Código", "Descrição", "Estado", "ECU"])
        layout.addWidget(self.codes_table, 2)
        monitor_row = QHBoxLayout()
        self.monitor_button = self.button("Consultar MIL e monitores", self.read_monitors, QStyle.StandardPixmap.SP_BrowserReload)
        monitor_row.addWidget(self.monitor_button)
        self.monitor_label = QLabel("MIL e prontidão: Não consultado")
        self.monitor_label.setWordWrap(True)
        monitor_row.addWidget(self.monitor_label, 1)
        layout.addLayout(monitor_row)
        self.monitor_table = self.table(["ECU", "MIL", "DTCs anunciados", "Motor", "Monitores suportados", "Consulta (local)", "Estado / motivo"])
        layout.addWidget(self.monitor_table, 1)
        self.freeze_label = QLabel("Freeze frame: não consultado")
        self.freeze_label.setWordWrap(True)
        layout.addWidget(self.freeze_label)
        self.freeze_table = self.table(["Parâmetro", "ECU", "Valor", "Unidade", "Disponibilidade"])
        layout.addWidget(self.freeze_table, 1)
        self.clear_label = QLabel()
        self.clear_label.setWordWrap(True)
        layout.addWidget(self.clear_label)

    def _ai_tab(self) -> None:
        layout = self.page("Análise por IA")
        self.symptoms = QPlainTextEdit()
        self.symptoms.setPlaceholderText("Sintomas observados")
        self.symptoms.setMaximumHeight(100)
        layout.addWidget(self.symptoms)
        row = QHBoxLayout()
        self.model = QLineEdit(self.settings.model)
        self.model.setMaximumWidth(230)
        self.daily = QSpinBox()
        self.daily.setRange(0, 2147483647)
        self.daily.setValue(self.settings.daily_limit)
        self.ai_interval = QSpinBox()
        self.ai_interval.setRange(0, 2147483647)
        self.ai_interval.setValue(self.settings.minimum_interval)
        self.ai_interval.setSuffix(" s")
        self.preview_button = self.button("Rever dados", self.preview_analysis)
        self.analyze_button = self.button("Analisar com Gemini", self.analyze)
        for widget in (QLabel("Modelo"), self.model, self.preview_button, self.analyze_button):
            row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)
        limits = QHBoxLayout()
        for widget in (QLabel("Limite diário"), self.daily, QLabel("Intervalo mínimo"), self.ai_interval):
            limits.addWidget(widget)
        limits.addStretch()
        layout.addLayout(limits)
        self.ai_availability = QLabel()
        self.ai_availability.setWordWrap(True)
        layout.addWidget(self.ai_availability)
        self.ai_status = QLabel("Sem pedido de análise")
        self.ai_status.setWordWrap(True)
        layout.addWidget(self.ai_status)
        self.analysis_validity = QLabel()
        self.analysis_validity.setWordWrap(True)
        layout.addWidget(self.analysis_validity)
        self.ai_views = QTabWidget()
        self.ai_input = QPlainTextEdit()
        self.ai_input.setReadOnly(True)
        self.ai_output = QPlainTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_views.addTab(self.ai_input, "Dados enviados")
        self.ai_views.addTab(self.ai_output, "Interpretação")
        layout.addWidget(self.ai_views)
        self.model.textChanged.connect(self.update_controls)
        self.daily.valueChanged.connect(self.update_controls)
        self.ai_interval.valueChanged.connect(self.update_controls)
        self.symptoms.textChanged.connect(self.render_analysis_validity)

    def _history_tab(self) -> None:
        layout = self.page("Histórico")
        row = QHBoxLayout()
        self.save_button = self.button("Guardar sessão", self.save_session, QStyle.StandardPixmap.SP_DialogSaveButton)
        self.refresh_button = self.button("Actualizar", self.refresh_history, QStyle.StandardPixmap.SP_BrowserReload)
        self.open_button = self.button("Abrir sessão", self.open_history, QStyle.StandardPixmap.SP_DialogOpenButton)
        self.export_button = self.button("Exportar JSON", self.export_history, QStyle.StandardPixmap.SP_DialogSaveButton)
        for button in (self.save_button, self.refresh_button, self.open_button, self.export_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.history_table = self.table(["ID", "Data (local)", "Origem", "Registo", "Verificação"])
        layout.addWidget(QLabel("Tipo de registo: fotografia da sessão; séries temporais não incluídas."))
        self.history_table.cellDoubleClicked.connect(lambda *_: self.open_history())
        layout.addWidget(self.history_table)

    def launch(self, category: str, operation: Callable, done: Callable, message: str) -> bool:
        if self.busy[category] or self.closing:
            return False
        self.busy[category] = True
        if category == "diag":
            self.service.cancel.clear()
        worker = Worker(operation)
        self.workers.append(worker)
        worker.signals.succeeded.connect(done, Qt.ConnectionType.QueuedConnection)
        worker.signals.failed.connect(lambda error: self.failed(category, error), Qt.ConnectionType.QueuedConnection)
        worker.signals.finished.connect(lambda: self.finished(category, worker), Qt.ConnectionType.QueuedConnection)
        self.statusBar().showMessage(message)
        self.update_controls()
        self.pools[category].start(worker)
        return True

    def failed(self, category: str, error: str) -> None:
        self.last_error = error
        if category == "diag":
            self.stop_polling()
            self.apply_state(self.service.session.to_dict())
        else:
            self.ai_status.setText(error)
        self.statusBar().showMessage(error)

    def finished(self, category: str, worker: Worker) -> None:
        self.busy[category] = False
        self.workers.remove(worker)
        self.update_controls()
        if self.closing and not any(self.busy.values()):
            QTimer.singleShot(0, self.close)
        elif category == "diag" and self.disconnect_pending:
            self.disconnect_pending = False
            self.disconnect_adapter()

    def update_controls(self, *_args) -> None:
        if not hasattr(self, "save_button"):
            return
        connected = self.state["adapter_status"] == "Ligado"
        diag_free = not self.busy["diag"] and not self.closing
        self.connect_button.setEnabled(diag_free and not connected)
        self.disconnect_button.setEnabled(connected or self.busy["diag"])
        for button in (self.read_button, self.codes_button, self.freeze_button, self.monitor_button):
            button.setEnabled(connected and diag_free)
        self.start_button.setEnabled(connected and diag_free and not self.poll_timer.isActive())
        self.stop_button.setEnabled(self.poll_timer.isActive())
        self.clear_button.setEnabled(connected and diag_free and self.state["simulation"])
        editable = diag_free and not connected
        tcp = self.kind.currentText() == "TCP"
        for widget in (self.kind, self.origin, self.timeout):
            widget.setEnabled(editable)
        for widget in (self.host, self.port):
            widget.setEnabled(editable and tcp)
        for widget in (self.serial_port, self.baud, self.scan_ports):
            widget.setEnabled(editable and not tcp)
        other_free = not self.busy["other"] and not self.closing
        for widget in (self.analyze_button, self.model, self.daily, self.ai_interval, self.save_button, self.refresh_button, self.open_button, self.export_button):
            widget.setEnabled(other_free)
        self.clear_button.setToolTip("Limpar registos não repara a causa. Apenas em simulação; guarda fotografia e pede confirmação.")
        self.pid_button.setEnabled(diag_free)
        self.render_connection()
        reason = self.gemini.unavailable_reason(self.model.text(), self.daily.value())
        self.ai_availability.setText("Indisponível: " + reason if reason else "Gemini configurado; validação remota ao solicitar análise.")

    def rescan_ports(self) -> None:
        current = self.serial_port.currentText()
        self.serial_port.clear()
        self.serial_port.addItems(available_ports())
        self.serial_port.setCurrentText(current)

    def connect_adapter(self) -> None:
        if not self.host.text().strip() and self.kind.currentText() == "TCP":
            self.statusBar().showMessage("Indique o host TCP.")
            return
        simulation = self.origin.currentData()
        if (self.simulator.ready and self.simulator.owned and self.kind.currentText() == "TCP"
                and self.host.text().strip().lower() in ("127.0.0.1", "localhost")
                and self.port.value() == self.simulator.port.value()):
            simulation = True
            self.origin.setCurrentIndex(self.origin.findData(True))
        if simulation is False and self.kind.currentText() == "TCP" and self.host.text().strip().lower() in ("127.0.0.1", "localhost", "::1"):
            answer = QMessageBox.question(self, "Confirmar origem", "A ligação TCP é local, mas a origem seleccionada é Veículo real.\nConfirma que esta ligação representa um veículo real?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        config = ConnectionConfig(self.kind.currentText(), self.host.text().strip(), self.port.value(), self.serial_port.currentText(), int(self.baud.currentText()), simulation, self.timeout.value())
        self.stop_polling()
        def connected(state):
            self.symptoms.clear()
            if self.last_analysis is None:
                self.ai_status.setText("Sem pedido de análise")
            self.apply_state(state)
            self.statusBar().showMessage("Ligação ao adaptador estabelecida.")
        self.launch("diag", lambda: self.service.connect(config), connected, "A ligar e consultar suporte OBD...")

    def disconnect_adapter(self) -> None:
        self.stop_polling()
        if self.busy["diag"]:
            self.service.cancel.set()
            self.disconnect_pending = True
            self.statusBar().showMessage("A cancelar e desligar...")
            return
        self.launch("diag", self.service.disconnect, self.apply_state, "A desligar...")

    def poll(self) -> None:
        selected = self.selected_pids()
        if self.launch("diag", lambda: self.service.poll(selected), self.apply_state, "A consultar parâmetros..."):
            self.readings_paused = False

    def start_polling(self) -> None:
        self.poll_timer.start(self.interval.value() * 1000)
        self.poll()
        self.update_controls()

    def stop_polling(self) -> None:
        self.poll_timer.stop()
        self.series.interrupt()
        self.readings_paused = True
        if hasattr(self, "data_table"):
            self.render_readings()
        self.update_controls()

    def read_codes(self) -> None:
        if self.launch("diag", self.service.read_codes, self.apply_state, "A consultar códigos confirmados e pendentes..."):
            pending = copy.deepcopy(self.state)
            pending["codes"] = []
            pending["code_queries"] = {kind: {"status": QUERYING} for kind in ("Confirmado", "Pendente")}
            self.apply_state(pending)

    def read_monitors(self) -> None:
        if self.launch("diag", self.service.read_monitor_status, self.apply_state, "A consultar MIL e prontidão..."):
            self.monitor_label.setText("MIL e prontidão: Consulta em curso")

    def read_freeze(self) -> None:
        if self.launch("diag", self.service.read_freeze_frame, self.apply_state, "A consultar freeze frame..."):
            pending = copy.deepcopy(self.state)
            pending["freeze_status"] = QUERYING
            pending["freeze_detail"] = ""
            self.apply_state(pending)

    def prepare_clear(self) -> None:
        if not self.state["simulation"]:
            return
        self.stop_polling()
        symptoms = self.symptoms.toPlainText()
        def prepare():
            self.service.poll()
            self.service.read_codes()
            self.service.read_freeze_frame()
            snapshot = self.service.session.to_dict()
            snapshot["symptoms"] = symptoms
            session_id = self.store.save(snapshot, "Fotografia antes da limpeza")
            return snapshot, session_id
        def prepared(result):
            snapshot, session_id = result
            self.apply_state(snapshot)
            # Espera pelo finished antes de permitir a operação seguinte.
            QTimer.singleShot(0, lambda: self.confirm_clear(session_id))
        self.launch("diag", prepare, prepared, "A guardar fotografia antes da limpeza...")

    def confirm_clear(self, session_id: int) -> None:
        if self.closing or self.disconnect_pending or self.state["adapter_status"] != "Ligado":
            return
        if self.busy["diag"]:
            QTimer.singleShot(20, lambda: self.confirm_clear(session_id))
            return
        answer = QMessageBox.question(self, "Limpeza na simulação", f"Fotografia guardada: sessão {session_id}.\nLimpar registos não repara a causa.\nEnviar o comando de limpeza ao emulador?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.launch("diag", self.service.clear_codes, self.apply_state, "A limpar e voltar a consultar códigos...")

    def apply_state(self, state: dict) -> None:
        # Campos de IA pertencem ao retrato enviado, não ao worker OBD.
        if state["created_at"] == self.state["created_at"]:
            for key in ("analysis", "analysis_input"):
                state[key] = self.state.get(key)
        self.state = state
        self.series.ingest(state)
        self.reading_chart.refresh()
        self.render_connection()
        self.render_readings()
        support = "; ".join(f"{ecu}: {', '.join(f'{pid:02X}' for pid in pids)}" for ecu, pids in state["supported"].items())
        failures = "; ".join(key + ": " + query.get("detail", query["status"]) for key, query in state.get("support_queries", {}).items() if query["status"] != "Consulta concluída")
        self.support_label.setText("PIDs anunciados (0100 → 0120 → 0140): " + (support or "Suporte ainda não confirmado") + (" | " + failures if failures else ""))
        self.fill_table(self.codes_table, [[c["code"], c["description"], c["status"], c["ecu"]] for c in state["codes"]])
        query_text = " | ".join(f"{kind}: {q['status']}" + (f" ({q['detail']})" if q.get("detail") else "") for kind, q in state["code_queries"].items())
        self.codes_status.setText(query_text or "Codigos ainda não consultados")
        self.freeze_label.setText("Freeze frame: " + state["freeze_status"] + (" | " + state["freeze_detail"] if state.get("freeze_detail") else "") + (" | " + json.dumps(state["freeze_codes"], ensure_ascii=False) if state["freeze_codes"] else ""))
        self.fill_table(self.freeze_table, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], r["status"]] for r in state["freeze_frame"]])
        self.clear_label.setText(state["clear_status"])
        query = state.get("monitor_query", {"status": "Não consultado"})
        self.monitor_label.setText("MIL e prontidão: " + query["status"] + (" | " + query["detail"] if query.get("detail") else ""))
        monitor_rows = []
        for ecu, status in state.get("monitor_status", {}).items():
            monitors = "; ".join(m["name"] + ": " + ("Concluído" if m["complete"] else "Incompleto") for m in status.get("monitors", []))
            monitor_rows.append([ecu, ("Acesa" if status["mil"] else "Apagada") if "mil" in status else "--",
                                 status.get("confirmed_count", "--"), status.get("engine_type", "--"), monitors or "--",
                                 self.local_time(status.get("timestamp")), status["status"] + (" | " + status["detail"] if status.get("detail") else "") + (" (desactualizado)" if state["adapter_status"] != "Ligado" else "")])
        self.fill_table(self.monitor_table, monitor_rows)
        if self.owns_connection() and self.simulator.ready and not self.closing:
            self.simulator.request("status")
        self.update_controls()

    def owns_connection(self) -> bool:
        connection = self.state.get("connection", {})
        return (self.simulator.ready and self.simulator.owned and connection.get("kind") == "TCP"
                and connection.get("host", "").lower() in ("localhost", "127.0.0.1")
                and connection.get("port") == self.simulator.port.value())

    def render_connection(self) -> None:
        state = self.state
        connection = state.get("connection", {})
        management = "Simulador gerido" if self.owns_connection() else ("Servidor externo" if connection.get("kind") == "TCP" else "Ligação serial" if connection.get("kind") else "Sem ligação")
        simulator = "Em execução" if self.simulator.ready else "A iniciar" if self.simulator.owned else "Parado (instância local)"
        polling = "Activas" if self.poll_timer.isActive() else "Paradas"
        self.connection_status.setText(f"Simulador: {simulator} | Scanner: {state['adapter_status']} | Consultas: {polling}\nSessão: {session_origin(state)} | {management} | ECU: {state['ecu_status']}")

    def change_simulator(self, action: str) -> None:
        if self.closing or self.simulator.transition:
            return
        if action == "reset":
            answer = QMessageBox.question(self, "Repor cenário", "Desligar a sessão gerida e invalidar os dados anteriores antes de repor o cenário?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        was_owned = self.owns_connection()
        self.simulator.transition = True
        self.simulator.update_controls()
        if was_owned:
            self.disconnect_adapter()
        def proceed():
            if self.closing:
                return
            if self.simulator.busy or (was_owned and (self.busy["diag"] or self.disconnect_pending)):
                QTimer.singleShot(30, proceed)
                return
            if was_owned:
                self.service.session = Session()
                self.apply_state(self.service.session.to_dict())
                self.symptoms.clear()
            if action == "stop":
                self.simulator.stop()
            else:
                self.simulator.request("reset")
            self.simulator.transition = False
            self.simulator.update_controls()
        proceed()

    def simulator_stopped(self, was_ready=False):
        if self.closing:
            QTimer.singleShot(0, self.close)
        elif was_ready:
            connection = self.state.get("connection", {})
            if connection.get("kind") == "TCP" and connection.get("host", "").lower() in ("localhost", "127.0.0.1") and connection.get("port") == self.simulator.port.value():
                self.disconnect_adapter()

    @staticmethod
    def local_time(timestamp: str | None) -> str:
        return datetime.fromisoformat(timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S") if timestamp else "--"

    @staticmethod
    def value_text(value) -> str:
        return f"{value:g}" if value is not None else "--"

    def snapshot(self) -> dict:
        snapshot = copy.deepcopy(self.state)
        snapshot["symptoms"] = self.symptoms.toPlainText()
        snapshot["freshness_seconds"] = max(10, self.interval.value() * 3)
        for reading in snapshot["readings"]:
            if reading["timestamp"] and reading["value"] is not None:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(reading["timestamp"])).total_seconds()
                if self.readings_paused or snapshot["adapter_status"] != "Ligado" or age > max(10, self.interval.value() * 3):
                    reading["stale"] = True
                    if reading["status"] == AVAILABLE:
                        reading["status"] = STALE
        return snapshot

    def render_readings(self) -> None:
        snapshot = self.snapshot()
        self.fill_table(self.data_table, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], self.local_time(r["timestamp"]), self.reading_status(r), r["detail"]] for r in snapshot["readings"]])
        self.render_analysis_validity()

    def render_analysis_validity(self) -> None:
        if not hasattr(self, "analysis_validity") or not hasattr(self, "symptoms"):
            return
        if self.last_analysis is None:
            self.analysis_validity.setText("Sem análise guardada para comparação")
            return
        try:
            current = analysis_payload(self.snapshot(), self.symptoms.toPlainText())
            changed = (self.last_analysis_session != self.state["created_at"] or
                       analysis_fingerprint(current) != analysis_fingerprint(self.last_analysis_input))
        except AnalysisError:
            changed = True
        self.analysis_validity.setText("Dados alterados desde esta análise" if changed else "Análise corresponde à fotografia dos dados actuais")

    @staticmethod
    def reading_status(reading: dict) -> str:
        status = reading["status"]
        return status + " (desactualizado)" if reading.get("stale") and status != STALE else status

    @staticmethod
    def fill_table(table: QTableWidget, rows: list[list]) -> None:
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                table.setItem(i, j, item)

    def preview_analysis(self) -> dict | None:
        try:
            payload = analysis_payload(self.snapshot(), self.symptoms.toPlainText())
        except AnalysisError as exc:
            self.ai_status.setText(str(exc))
            return None
        self.ai_input.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))
        self.ai_views.setCurrentIndex(0)
        return payload

    def analyze(self) -> None:
        payload = self.preview_analysis()
        if payload is None:
            return
        self.settings.daily_limit = self.daily.value()
        self.settings.minimum_interval = self.ai_interval.value()
        session_token = self.state["created_at"]
        model = self.model.text().strip()
        self.ai_status.setText("A aguardar Gemini...")
        def analyzed(result):
            self.last_analysis = result
            self.last_analysis_input = result.get("analysis_input", payload)
            self.last_analysis_session = session_token
            if session_token != self.state["created_at"]:
                self.ai_status.setText("Análise concluída para a sessão anterior; resultado não associado a esta ligação.")
            else:
                self.state["analysis"] = result
                self.state["analysis_input"] = self.last_analysis_input
            output = []
            for key, values in result["result"].items():
                output.append(ANALYSIS_LABELS.get(key, key.replace("_", " ").capitalize()) + ":")
                output.extend("- " + value for value in values)
                output.append("")
            self.ai_output.setPlainText("\n".join(output))
            self.ai_views.setCurrentIndex(1)
            prefix = "Cache local; sem nova chamada. Tokens da resposta original: " if result["cache"] else "Análise concluída. Tokens informados pela API: "
            self.ai_status.setText(prefix + json.dumps(result["tokens"], ensure_ascii=False) + " | Captura: " + self.local_time(result.get("captured_at")) + " | Resposta original: " + self.local_time(result.get("analyzed_at")))
            self.ai_input.setPlainText(json.dumps(self.last_analysis_input, ensure_ascii=False, indent=2))
            self.render_analysis_validity()
        self.launch("other", lambda: self.gemini.analyze(payload, model), analyzed, "A analisar a fotografia da sessão...")

    def save_session(self) -> None:
        snapshot = self.snapshot()
        def saved(session_id):
            self.statusBar().showMessage(f"Sessão {session_id} guardada.")
            QTimer.singleShot(50, self.refresh_history)
        self.launch("other", lambda: self.store.save(snapshot), saved, "A guardar sessão...")

    def refresh_history(self) -> None:
        def loaded(rows):
            self.history_rows = rows
            self.fill_table(self.history_table, [[r["id"], self.local_time(r["created_at"]), r["origin"], r["label"], r.get("origin_note", "")] for r in rows])
        self.launch("other", self.store.list_sessions, loaded, "A consultar histórico...")

    def selected_session_id(self) -> int | None:
        row = self.history_table.currentRow()
        return self.history_rows[row]["id"] if 0 <= row < len(self.history_rows) else None

    def open_history(self) -> None:
        session_id = self.selected_session_id()
        if session_id is None:
            self.statusBar().showMessage("Selecione uma sessão no histórico.")
            return
        def opened(snapshot):
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Sessão {session_id} | {self.local_time(snapshot['created_at'])}")
            dialog.resize(850, 620)
            layout = QVBoxLayout(dialog)
            try:
                origin = session_origin(snapshot)
            except OriginError:
                origin = "Origem por confirmar; registo original preservado"
            summary = QLabel(f"{origin} | Sessão guardada | {self.local_time(snapshot['created_at'])}")
            summary.setWordWrap(True)
            layout.addWidget(summary)
            views = QTabWidget()
            layout.addWidget(views)
            readings = self.table(["Parâmetro", "ECU", "Valor", "Unidade", "Instante", "Estado"])
            self.fill_table(readings, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], self.local_time(r["timestamp"]), r["status"]] for r in snapshot["readings"]])
            views.addTab(readings, "Dados")
            codes_page = QWidget()
            codes_layout = QVBoxLayout(codes_page)
            query_status = QLabel(" | ".join(f"{kind}: {query['status']}" for kind, query in snapshot["code_queries"].items()) or "Codigos não consultados")
            query_status.setWordWrap(True)
            codes_layout.addWidget(query_status)
            codes = self.table(["Código", "Descrição", "Estado", "ECU"])
            self.fill_table(codes, [[c["code"], c["description"], c["status"], c["ecu"]] for c in snapshot["codes"]])
            codes_layout.addWidget(codes)
            views.addTab(codes_page, "Avarias")
            monitor = self.table(["ECU", "MIL", "DTCs anunciados", "Motor", "Monitores", "Consulta (local)", "Estado"])
            self.fill_table(monitor, [[ecu, ("Acesa" if s["mil"] else "Apagada") if "mil" in s else "--",
                                      s.get("confirmed_count", "--"), s.get("engine_type", "--"),
                                      "; ".join(m["name"] + ": " + ("Concluído" if m["complete"] else "Incompleto") for m in s.get("monitors", [])),
                                      self.local_time(s.get("timestamp")), s["status"]] for ecu, s in snapshot.get("monitor_status", {}).items()])
            views.addTab(monitor, "MIL e prontidão")
            freeze_page = QWidget()
            freeze_layout = QVBoxLayout(freeze_page)
            freeze_label = QLabel(snapshot["freeze_status"] + (" | " + snapshot["freeze_detail"] if snapshot.get("freeze_detail") else ""))
            freeze_label.setWordWrap(True)
            freeze_layout.addWidget(freeze_label)
            freeze = self.table(["Parâmetro", "ECU", "Valor", "Unidade", "Estado"])
            self.fill_table(freeze, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], r["status"]] for r in snapshot["freeze_frame"]])
            freeze_layout.addWidget(freeze)
            views.addTab(freeze_page, "Freeze frame")
            analysis_view = QPlainTextEdit()
            analysis_view.setReadOnly(True)
            content = ["Sintomas:", snapshot["symptoms"] or "Não registados", ""]
            if snapshot.get("analysis"):
                content.append("Modelo: " + snapshot["analysis"]["model"])
                content.append("Captura: " + self.local_time(snapshot["analysis"].get("captured_at")))
                content.append("Resposta original: " + self.local_time(snapshot["analysis"].get("analyzed_at")))
                for key, values in snapshot["analysis"]["result"].items():
                    content.append("\n" + ANALYSIS_LABELS.get(key, key.replace("_", " ").capitalize()) + ":")
                    content.extend("- " + value for value in values)
            else:
                content.append("Sem análise Gemini guardada")
            analysis_view.setPlainText("\n".join(content))
            views.addTab(analysis_view, "Sintomas e análise")
            if snapshot.get("analysis_input"):
                sent = QPlainTextEdit()
                sent.setReadOnly(True)
                sent.setPlainText(json.dumps(snapshot["analysis_input"], ensure_ascii=False, indent=2))
                views.addTab(sent, "Dados enviados")
            layout.addWidget(self.button("Fechar", dialog.close, QStyle.StandardPixmap.SP_DialogCloseButton))
            dialog.show()
        self.launch("other", lambda: self.store.load(session_id), opened, "A abrir sessão...")

    def export_history(self) -> None:
        session_id = self.selected_session_id()
        if session_id is None:
            self.statusBar().showMessage("Selecione uma sessão no histórico.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar sessão", f"sessão-{session_id}.json", "JSON (*.json)")
        if path:
            self.launch("other", lambda: self.store.export(session_id, Path(path)), lambda _: self.statusBar().showMessage("Sessão exportada em JSON."), "A exportar sessão...")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing = True
        self.simulator.setEnabled(False)
        self.poll_timer.stop()
        self.age_timer.stop()
        self.service.cancel.set()
        if self.simulator.owned:
            self.simulator.stop()
            event.ignore()
            return
        if self.simulator.busy:
            event.ignore()
            QTimer.singleShot(50, self.close)
            return
        if any(self.busy.values()):
            event.ignore()
            self.statusBar().showMessage("A encerrar operações; a chamada Gemini termina no seu timeout...")
            self.update_controls()
            return
        self.service.disconnect()
        for pool in self.pools.values():
            pool.waitForDone(100)
        event.accept()
