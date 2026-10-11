from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QLabel, QTabWidget, QPlainTextEdit, QMenu, QStyle)
from PySide6.QtGui import QAction
from scanner_outo.models import origin_label
from scanner_outo.communication.serial_transport import available_ports
from scanner_outo.diagnostics.obd import PIDS, DEFAULT_PIDS
from scanner_outo.ui.charts import ReadingChart
from scanner_outo.ui.components import Panel, Columns, label


def build(self):
    layout = self.page("Histórico")
    row = QHBoxLayout()
    self.save_button = self.button("Guardar sessão", self.save_session, QStyle.StandardPixmap.SP_DialogSaveButton)
    self.refresh_button = self.button("Actualizar", self.refresh_history, QStyle.StandardPixmap.SP_BrowserReload)
    self.open_button = self.button("Abrir sessão", self.open_history, QStyle.StandardPixmap.SP_DialogOpenButton)
    self.export_button = self.button("Exportar JSON", self.export_history, QStyle.StandardPixmap.SP_DialogSaveButton)
    for button in (self.save_button, self.refresh_button):
        row.addWidget(button)
    row.addStretch()
    layout.addLayout(row)
    self.history_table = self.table(["ID", "Data (local)", "Origem", "Registo", "Verificação"])
    layout.addWidget(QLabel("Tipo de registo: fotografia da sessão; séries temporais não incluídas."))
    self.history_table.cellDoubleClicked.connect(lambda *_: self.open_history())
    archive = Panel("Arquivo de sessões")
    archive.body.addWidget(self.history_table)
    self.history_table.setMinimumHeight(360)
    self.history_detail = label("Nenhuma sessão seleccionada", "secondary")
    detail = Panel("Fotografia seleccionada")
    detail.body.addWidget(self.history_detail)
    detail.body.addWidget(self.open_button)
    detail.body.addWidget(self.export_button)
    detail.body.addStretch()
    layout.addWidget(Columns([archive, detail]))
    def selected():
        row = self.history_table.currentRow()
        if 0 <= row < len(self.history_rows):
            record = self.history_rows[row]
            self.history_detail.setText(f"Sessão {record['id']} · {record['origin']}\n{record['label']} · {self.local_time(record['created_at'])}")
        else:
            self.history_detail.setText("Nenhuma sessão seleccionada")
    self.history_table.itemSelectionChanged.connect(selected)
