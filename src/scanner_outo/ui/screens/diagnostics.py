from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QLabel, QTabWidget, QPlainTextEdit, QMenu, QStyle)
from PySide6.QtGui import QAction
from scanner_outo.models import origin_label
from scanner_outo.communication.serial_transport import available_ports
from scanner_outo.diagnostics.obd import PIDS, DEFAULT_PIDS
from scanner_outo.ui.charts import ReadingChart
from scanner_outo.ui.components import Panel, Columns, label


def build(self):
    layout = self.page("Avarias")
    self.codes_button = self.button("Consultar avarias", self.read_codes, QStyle.StandardPixmap.SP_BrowserReload)
    self.freeze_button = self.button("Consultar freeze frame", self.read_freeze)
    self.clear_button = self.button("Limpar registos", self.prepare_clear, QStyle.StandardPixmap.SP_TrashIcon)
    layout.addWidget(Columns([self.codes_button, self.freeze_button, self.clear_button], maximum=3))
    self.codes_status = QLabel("Não consultado")
    self.codes_status.setWordWrap(True)
    layout.addWidget(self.codes_status)
    self.diagnostic_views = QTabWidget()
    codes_page = QWidget()
    codes_layout = QVBoxLayout(codes_page)
    freeze_page = QWidget()
    freeze_layout = QVBoxLayout(freeze_page)
    monitor_page = QWidget()
    monitor_layout = QVBoxLayout(monitor_page)
    self.diagnostic_views.addTab(codes_page, "Confirmados e pendentes")
    self.diagnostic_views.addTab(freeze_page, "Freeze frame")
    self.diagnostic_views.addTab(monitor_page, "Prontidão")
    self.diagnostic_views.setMinimumHeight(500)
    layout.addWidget(self.diagnostic_views)
    self.codes_table = self.table(["Código", "Descrição", "Estado", "ECU"])
    codes_layout.addWidget(self.codes_table, 2)
    detail = Panel("Detalhe do código seleccionado")
    self.dtc_detail = label("Nenhum código seleccionado")
    detail.body.addWidget(self.dtc_detail)
    def selected():
        row = self.codes_table.currentRow()
        if 0 <= row < len(self.state["codes"]):
            code = self.state["codes"][row]
            self.dtc_detail.setText(f"{code['code']} · {code['description']}\n{code['status']} · ECU {code['ecu']}\nO código descreve uma condição detectada; não identifica uma peça avariada.")
        else:
            self.dtc_detail.setText("Nenhum código seleccionado")
    self.codes_table.itemSelectionChanged.connect(selected)
    codes_layout.addWidget(detail)
    monitor_row = QHBoxLayout()
    self.monitor_button = self.button("Consultar MIL e monitores", self.read_monitors, QStyle.StandardPixmap.SP_BrowserReload)
    monitor_row.addWidget(self.monitor_button)
    self.monitor_label = QLabel("MIL e prontidão: Não consultado")
    self.monitor_label.setWordWrap(True)
    monitor_row.addWidget(self.monitor_label, 1)
    layout.insertLayout(1, monitor_row)
    self.monitor_table = self.table(["ECU", "MIL", "DTCs anunciados", "Motor", "Monitores suportados", "Consulta (local)", "Estado / motivo"])
    monitor_layout.addWidget(self.monitor_table, 1)
    self.freeze_label = QLabel("Freeze frame: não consultado")
    self.freeze_label.setWordWrap(True)
    freeze_layout.addWidget(self.freeze_label)
    self.freeze_table = self.table(["Parâmetro", "ECU", "Valor", "Unidade", "Disponibilidade", "Detalhe"])
    freeze_layout.addWidget(self.freeze_table, 1)
    self.freeze_table.setMinimumHeight(300)
    self.clear_label = QLabel()
    self.clear_label.setWordWrap(True)
    layout.addWidget(self.clear_label)
