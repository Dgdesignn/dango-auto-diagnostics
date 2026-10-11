from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QLabel, QTabWidget, QPlainTextEdit, QMenu, QStyle)
from PySide6.QtGui import QAction
from scanner_outo.models import origin_label
from scanner_outo.communication.serial_transport import available_ports
from scanner_outo.diagnostics.obd import PIDS, DEFAULT_PIDS
from scanner_outo.ui.charts import ReadingChart
from scanner_outo.ui.components import Panel, Columns, TechnicalSection
from PySide6.QtWidgets import QCheckBox, QGridLayout


def build(self):
    layout = self.page("Dados")
    self.read_button = self.button("Actualizar", self.poll, QStyle.StandardPixmap.SP_BrowserReload)
    self.start_button = self.button("Iniciar actualização", self.start_polling, QStyle.StandardPixmap.SP_MediaPlay)
    self.stop_button = self.button("Parar", self.stop_polling, QStyle.StandardPixmap.SP_MediaStop)
    self.interval = QSpinBox()
    self.interval.setRange(2, 60)
    self.interval.setValue(3)
    self.interval.setSuffix(" s")
    self.interval.valueChanged.connect(lambda value: self.poll_timer.setInterval(value * 1000))
    interval_control = QWidget()
    interval_row = QHBoxLayout(interval_control)
    interval_row.setContentsMargins(0, 0, 0, 0)
    interval_row.addWidget(QLabel("Intervalo"))
    interval_row.addWidget(self.interval)
    layout.addWidget(Columns([self.read_button, self.start_button, self.stop_button, interval_control], maximum=4))
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
    parameters = Panel("Parâmetros OBD-II")
    self.pid_checks = {}
    for index, (pid, definition) in enumerate(PIDS.items()):
        check = QCheckBox(f"{pid:02X} · {definition.name}")
        check.setToolTip(f"{definition.name} ({definition.unit})")
        check.setChecked(self.pid_actions[pid].isChecked())
        check.toggled.connect(self.pid_actions[pid].setChecked)
        self.pid_actions[pid].toggled.connect(check.setChecked)
        self.pid_checks[pid] = check
    parameters.body.addWidget(Columns(list(self.pid_checks.values()), breakpoint=720))
    layout.addWidget(parameters)
    self.data_table = self.table(["Parâmetro", "ECU", "Valor", "Unidade", "Leitura (local)", "Disponibilidade", "Detalhe"])
    self.data_views = QTabWidget()
    self.data_views.addTab(self.data_table, "Leituras")
    self.reading_chart = ReadingChart(self.series)
    self.data_views.addTab(self.reading_chart, "Gráfico")
    layout.addWidget(self.data_views, 1)
    self.data_views.setMinimumHeight(360)
    self.support_label = QLabel()
    self.support_label.setWordWrap(True)
    layout.addWidget(TechnicalSection("Detalhes técnicos · mapas de suporte", self.support_label))
    self.stop_button.setToolTip("Parar consultas conserva os pontos e não encerra o simulador.")
    self.selection_changed()
