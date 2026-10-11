from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPlainTextEdit, QMessageBox, QFileDialog, QDialog, QStyle,
)

from scanner_outo.config import Settings
from scanner_outo.communication.serial_transport import available_ports
from scanner_outo.models import ConnectionConfig
from scanner_outo.services import DiagnosticService
from scanner_outo.persistence import SessionStore
from scanner_outo.gemini import GeminiService, analysis_payload, AnalysisError
from scanner_outo.ui.workers import Worker


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
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
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.age_timer = QTimer(self)
        self.age_timer.timeout.connect(self.render_readings)
        self.setWindowTitle("Scanner Outo | Diagnostico automovel")
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
        self.setStyleSheet("""
            QMainWindow, QDialog { background: #f4f6f8; }
            QLabel { color: #202b33; }
            QTabWidget::pane { border: 1px solid #ccd3da; background: white; }
            QTabBar::tab { padding: 10px 18px; }
            QTabBar::tab:selected { background: white; color: #006c67; }
            QPushButton { padding: 7px 12px; border-radius: 4px; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { min-height: 26px; }
            QTableWidget { gridline-color: #e1e5e9; selection-background-color: #d1e8e6; selection-color: #202b33; }
        """)
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
        layout = self.page("Ligacao")
        form = QFormLayout()
        self.kind = QComboBox()
        self.kind.addItems(["TCP", "Serial USB", "Bluetooth SPP"])
        self.origin = QComboBox()
        self.origin.addItems(["Emulador / simulacao", "Veiculo real"])
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
        self.scan_ports = self.button("", self.rescan_ports, QStyle.StandardPixmap.SP_BrowserReload)
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
        self.read_button = self.button("Consultar agora", self.poll, QStyle.StandardPixmap.SP_BrowserReload)
        self.start_button = self.button("Iniciar actualizacao", self.start_polling, QStyle.StandardPixmap.SP_MediaPlay)
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
        self.data_table = self.table(["Parametro", "ECU", "Valor", "Unidade", "Leitura (local)", "Disponibilidade", "Detalhe"])
        layout.addWidget(self.data_table)
        self.support_label = QLabel()
        self.support_label.setWordWrap(True)
        layout.addWidget(self.support_label)

    def _codes_tab(self) -> None:
        layout = self.page("Avarias")
        row = QHBoxLayout()
        self.codes_button = self.button("Consultar avarias", self.read_codes, QStyle.StandardPixmap.SP_BrowserReload)
        self.freeze_button = self.button("Consultar freeze frame", self.read_freeze)
        self.clear_button = self.button("Limpar na simulacao", self.prepare_clear, QStyle.StandardPixmap.SP_TrashIcon)
        for button in (self.codes_button, self.freeze_button, self.clear_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.codes_status = QLabel("Nao consultado")
        self.codes_status.setWordWrap(True)
        layout.addWidget(self.codes_status)
        self.codes_table = self.table(["Codigo", "Descricao", "Estado", "ECU"])
        layout.addWidget(self.codes_table, 2)
        self.freeze_label = QLabel("Freeze frame: nao consultado")
        self.freeze_label.setWordWrap(True)
        layout.addWidget(self.freeze_label)
        self.freeze_table = self.table(["Parametro", "ECU", "Valor", "Unidade", "Disponibilidade"])
        layout.addWidget(self.freeze_table, 1)
        self.clear_label = QLabel()
        self.clear_label.setWordWrap(True)
        layout.addWidget(self.clear_label)

    def _ai_tab(self) -> None:
        layout = self.page("Analise por IA")
        self.symptoms = QPlainTextEdit()
        self.symptoms.setPlaceholderText("Sintomas observados")
        self.symptoms.setMaximumHeight(100)
        layout.addWidget(self.symptoms)
        row = QHBoxLayout()
        self.model = QLineEdit(self.settings.model)
        self.model.setMaximumWidth(230)
        self.daily = QSpinBox()
        self.daily.setRange(0, 1000)
        self.daily.setValue(self.settings.daily_limit)
        self.ai_interval = QSpinBox()
        self.ai_interval.setRange(0, 3600)
        self.ai_interval.setValue(self.settings.minimum_interval)
        self.ai_interval.setSuffix(" s")
        self.preview_button = self.button("Rever dados", self.preview_analysis)
        self.analyze_button = self.button("Analisar com Gemini", self.analyze)
        for widget in (QLabel("Modelo"), self.model, self.preview_button, self.analyze_button):
            row.addWidget(widget)
        row.addStretch()
        layout.addLayout(row)
        limits = QHBoxLayout()
        for widget in (QLabel("Limite diario"), self.daily, QLabel("Intervalo minimo"), self.ai_interval):
            limits.addWidget(widget)
        limits.addStretch()
        layout.addLayout(limits)
        self.ai_status = QLabel("Sem pedido de analise")
        self.ai_status.setWordWrap(True)
        layout.addWidget(self.ai_status)
        self.ai_views = QTabWidget()
        self.ai_input = QPlainTextEdit()
        self.ai_input.setReadOnly(True)
        self.ai_output = QPlainTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_views.addTab(self.ai_input, "Dados enviados")
        self.ai_views.addTab(self.ai_output, "Interpretacao")
        layout.addWidget(self.ai_views)

    def _history_tab(self) -> None:
        layout = self.page("Historico")
        row = QHBoxLayout()
        self.save_button = self.button("Guardar sessao", self.save_session, QStyle.StandardPixmap.SP_DialogSaveButton)
        self.refresh_button = self.button("Actualizar", self.refresh_history, QStyle.StandardPixmap.SP_BrowserReload)
        self.open_button = self.button("Abrir sessao", self.open_history, QStyle.StandardPixmap.SP_DialogOpenButton)
        self.export_button = self.button("Exportar JSON", self.export_history, QStyle.StandardPixmap.SP_DialogSaveButton)
        for button in (self.save_button, self.refresh_button, self.open_button, self.export_button):
            row.addWidget(button)
        row.addStretch()
        layout.addLayout(row)
        self.history_table = self.table(["ID", "Data (local)", "Origem", "Registo"])
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
        for button in (self.read_button, self.codes_button, self.freeze_button):
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

    def rescan_ports(self) -> None:
        current = self.serial_port.currentText()
        self.serial_port.clear()
        self.serial_port.addItems(available_ports())
        self.serial_port.setCurrentText(current)

    def connect_adapter(self) -> None:
        if not self.host.text().strip() and self.kind.currentText() == "TCP":
            self.statusBar().showMessage("Indique o host TCP.")
            return
        config = ConnectionConfig(self.kind.currentText(), self.host.text().strip(), self.port.value(), self.serial_port.currentText(), int(self.baud.currentText()), self.origin.currentIndex() == 0, self.timeout.value())
        self.stop_polling()
        def connected(state):
            self.symptoms.clear()
            self.ai_input.clear()
            self.ai_output.clear()
            self.ai_status.setText("Sem pedido de analise")
            self.apply_state(state)
            self.statusBar().showMessage("Ligacao ao adaptador estabelecida.")
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
        self.launch("diag", self.service.poll, self.apply_state, "A consultar parametros...")

    def start_polling(self) -> None:
        self.poll_timer.start(self.interval.value() * 1000)
        self.poll()
        self.update_controls()

    def stop_polling(self) -> None:
        self.poll_timer.stop()
        self.update_controls()

    def read_codes(self) -> None:
        self.launch("diag", self.service.read_codes, self.apply_state, "A consultar codigos confirmados e pendentes...")

    def read_freeze(self) -> None:
        self.launch("diag", self.service.read_freeze_frame, self.apply_state, "A consultar freeze frame...")

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
            # Espera pelo finished antes de permitir a operacao seguinte.
            QTimer.singleShot(0, lambda: self.confirm_clear(session_id))
        self.launch("diag", prepare, prepared, "A guardar fotografia antes da limpeza...")

    def confirm_clear(self, session_id: int) -> None:
        if self.closing or self.disconnect_pending or self.state["adapter_status"] != "Ligado":
            return
        if self.busy["diag"]:
            QTimer.singleShot(20, lambda: self.confirm_clear(session_id))
            return
        answer = QMessageBox.question(self, "Limpeza na simulacao", f"Fotografia guardada: sessao {session_id}.\nLimpar registos nao repara a causa.\nEnviar o comando de limpeza ao emulador?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.launch("diag", self.service.clear_codes, self.apply_state, "A limpar e voltar a consultar codigos...")

    def apply_state(self, state: dict) -> None:
        # Campos de IA pertencem ao retrato enviado, nao ao worker OBD.
        if state["created_at"] == self.state["created_at"]:
            for key in ("analysis", "analysis_input"):
                state[key] = self.state.get(key)
        self.state = state
        origin = "EMULADOR / SIMULACAO" if state["simulation"] else "VEICULO REAL"
        self.connection_status.setText(f"{origin}   |   Adaptador: {state['adapter_status']}   |   ECU: {state['ecu_status']}")
        self.render_readings()
        support = "; ".join(f"{ecu}: {', '.join(f'{pid:02X}' for pid in pids)}" for ecu, pids in state["supported"].items())
        self.support_label.setText("PIDs anunciados (01 00): " + (support or "Suporte ainda nao confirmado"))
        self.fill_table(self.codes_table, [[c["code"], c["description"], c["status"], c["ecu"]] for c in state["codes"]])
        query_text = " | ".join(f"{kind}: {q['status']}" + (f" ({q['detail']})" if q.get("detail") else "") for kind, q in state["code_queries"].items())
        self.codes_status.setText(query_text or "Codigos ainda nao consultados")
        self.freeze_label.setText("Freeze frame: " + state["freeze_status"] + (" | " + json.dumps(state["freeze_codes"], ensure_ascii=False) if state["freeze_codes"] else ""))
        self.fill_table(self.freeze_table, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], r["status"]] for r in state["freeze_frame"]])
        self.clear_label.setText(state["clear_status"])
        self.update_controls()

    @staticmethod
    def local_time(timestamp: str | None) -> str:
        return datetime.fromisoformat(timestamp).astimezone().strftime("%Y-%m-%d %H:%M:%S") if timestamp else "--"

    @staticmethod
    def value_text(value) -> str:
        return f"{value:g}" if value is not None else "--"

    def snapshot(self) -> dict:
        snapshot = copy.deepcopy(self.state)
        snapshot["symptoms"] = self.symptoms.toPlainText()
        for reading in snapshot["readings"]:
            if reading["timestamp"] and reading["value"] is not None:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(reading["timestamp"])).total_seconds()
                if age > max(10, self.interval.value() * 3) and reading["status"] == "Disponivel":
                    reading["status"] = "Desactualizado"
        return snapshot

    def render_readings(self) -> None:
        snapshot = self.snapshot()
        self.fill_table(self.data_table, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], self.local_time(r["timestamp"]), r["status"], r["detail"]] for r in snapshot["readings"]])

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
            if session_token != self.state["created_at"]:
                self.ai_status.setText("Analise concluida para a sessao anterior; resultado nao associado a esta ligacao.")
                return
            self.state["analysis"] = result
            self.state["analysis_input"] = payload
            output = []
            for key, values in result["result"].items():
                output.append(key.replace("_", " ").capitalize() + ":")
                output.extend("- " + value for value in values)
                output.append("")
            self.ai_output.setPlainText("\n".join(output))
            self.ai_views.setCurrentIndex(1)
            prefix = "Cache local; sem nova chamada. Tokens da resposta original: " if result["cache"] else "Analise concluida. Tokens informados pela API: "
            self.ai_status.setText(prefix + json.dumps(result["tokens"], ensure_ascii=False))
        self.launch("other", lambda: self.gemini.analyze(payload, model), analyzed, "A analisar a fotografia da sessao...")

    def save_session(self) -> None:
        snapshot = self.snapshot()
        def saved(session_id):
            self.statusBar().showMessage(f"Sessao {session_id} guardada.")
            QTimer.singleShot(50, self.refresh_history)
        self.launch("other", lambda: self.store.save(snapshot), saved, "A guardar sessao...")

    def refresh_history(self) -> None:
        def loaded(rows):
            self.history_rows = rows
            self.fill_table(self.history_table, [[r["id"], self.local_time(r["created_at"]), r["origin"], r["label"]] for r in rows])
        self.launch("other", self.store.list_sessions, loaded, "A consultar historico...")

    def selected_session_id(self) -> int | None:
        row = self.history_table.currentRow()
        return self.history_rows[row]["id"] if 0 <= row < len(self.history_rows) else None

    def open_history(self) -> None:
        session_id = self.selected_session_id()
        if session_id is None:
            self.statusBar().showMessage("Selecione uma sessao no historico.")
            return
        def opened(snapshot):
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Sessao {session_id} | {self.local_time(snapshot['created_at'])}")
            dialog.resize(850, 620)
            layout = QVBoxLayout(dialog)
            origin = "Emulador / simulacao" if snapshot["simulation"] else "Veiculo real"
            summary = QLabel(f"{origin} | Sessao guardada | {self.local_time(snapshot['created_at'])}")
            summary.setWordWrap(True)
            layout.addWidget(summary)
            views = QTabWidget()
            layout.addWidget(views)
            readings = self.table(["Parametro", "ECU", "Valor", "Unidade", "Instante", "Estado"])
            self.fill_table(readings, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], self.local_time(r["timestamp"]), r["status"]] for r in snapshot["readings"]])
            views.addTab(readings, "Dados")
            codes_page = QWidget()
            codes_layout = QVBoxLayout(codes_page)
            query_status = QLabel(" | ".join(f"{kind}: {query['status']}" for kind, query in snapshot["code_queries"].items()) or "Codigos nao consultados")
            query_status.setWordWrap(True)
            codes_layout.addWidget(query_status)
            codes = self.table(["Codigo", "Descricao", "Estado", "ECU"])
            self.fill_table(codes, [[c["code"], c["description"], c["status"], c["ecu"]] for c in snapshot["codes"]])
            codes_layout.addWidget(codes)
            views.addTab(codes_page, "Avarias")
            freeze_page = QWidget()
            freeze_layout = QVBoxLayout(freeze_page)
            freeze_label = QLabel(snapshot["freeze_status"])
            freeze_label.setWordWrap(True)
            freeze_layout.addWidget(freeze_label)
            freeze = self.table(["Parametro", "ECU", "Valor", "Unidade", "Estado"])
            self.fill_table(freeze, [[r["name"], r["ecu"], self.value_text(r["value"]), r["unit"], r["status"]] for r in snapshot["freeze_frame"]])
            freeze_layout.addWidget(freeze)
            views.addTab(freeze_page, "Freeze frame")
            analysis_view = QPlainTextEdit()
            analysis_view.setReadOnly(True)
            content = ["Sintomas:", snapshot["symptoms"] or "Nao registados", ""]
            if snapshot.get("analysis"):
                content.append("Modelo: " + snapshot["analysis"]["model"])
                for key, values in snapshot["analysis"]["result"].items():
                    content.append("\n" + key.replace("_", " ").capitalize() + ":")
                    content.extend("- " + value for value in values)
            else:
                content.append("Sem analise Gemini guardada")
            analysis_view.setPlainText("\n".join(content))
            views.addTab(analysis_view, "Sintomas e analise")
            if snapshot.get("analysis_input"):
                sent = QPlainTextEdit()
                sent.setReadOnly(True)
                sent.setPlainText(json.dumps(snapshot["analysis_input"], ensure_ascii=False, indent=2))
                views.addTab(sent, "Dados enviados")
            layout.addWidget(self.button("Fechar", dialog.close, QStyle.StandardPixmap.SP_DialogCloseButton))
            dialog.show()
        self.launch("other", lambda: self.store.load(session_id), opened, "A abrir sessao...")

    def export_history(self) -> None:
        session_id = self.selected_session_id()
        if session_id is None:
            self.statusBar().showMessage("Selecione uma sessao no historico.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar sessao", f"sessao-{session_id}.json", "JSON (*.json)")
        if path:
            self.launch("other", lambda: self.store.export(session_id, Path(path)), lambda _: self.statusBar().showMessage("Sessao exportada em JSON."), "A exportar sessao...")

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing = True
        self.poll_timer.stop()
        self.age_timer.stop()
        self.service.cancel.set()
        if any(self.busy.values()):
            event.ignore()
            self.statusBar().showMessage("A encerrar operacoes; a chamada Gemini termina no seu timeout...")
            self.update_controls()
            return
        self.service.disconnect()
        for pool in self.pools.values():
            pool.waitForDone(100)
        event.accept()
