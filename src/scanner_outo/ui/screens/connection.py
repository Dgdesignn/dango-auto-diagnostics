from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QSpinBox, QDoubleSpinBox, QLabel, QTabWidget, QPlainTextEdit, QMenu, QStyle)
from PySide6.QtGui import QAction
from scanner_outo.models import origin_label
from scanner_outo.communication.serial_transport import available_ports
from scanner_outo.diagnostics.obd import PIDS, DEFAULT_PIDS
from scanner_outo.ui.charts import ReadingChart
from scanner_outo.ui.components import Panel, Columns, label
from scanner_outo.ui.design import icon
from PySide6.QtWidgets import QPushButton, QButtonGroup


def build(self):
    layout = self.page("Ligação")
    parameters = Panel("Parâmetros da ligação")
    status = Panel("Estado do adaptador e da ECU")
    status.body.addWidget(self.connection_status)
    self.connection_status.setProperty("notice", True)
    status.body.addWidget(label("Veículo: Não identificado", "secondary"))
    status.body.addStretch()
    self.transport_choices = []
    self.transport_group = QButtonGroup(self)
    self.transport_group.setExclusive(True)
    for title in ("TCP", "Serial USB", "Bluetooth SPP"):
        choice = QPushButton(icon("cable"), title)
        choice.setCheckable(True)
        self.transport_group.addButton(choice)
        choice.setProperty("choice", True)
        choice.setAccessibleName(title)
        choice.clicked.connect(lambda checked=False, value=title: self.kind.setCurrentText(value))
        parameters.body.addWidget(choice)
        self.transport_choices.append(choice)
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
    for title, widget in (("Tipo", self.kind), ("Origem", self.origin), ("Host TCP", self.host), ("Porta TCP", self.port), ("Porta COM / Bluetooth SPP", serial_row), ("Baud rate", self.baud), ("Timeout por pedido", self.timeout)):
        form.addRow(title, widget)
    form.setSpacing(12)
    parameters.body.addLayout(form)
    buttons = QHBoxLayout()
    self.connect_button = self.button("Ligar", self.connect_adapter, QStyle.StandardPixmap.SP_DialogApplyButton)
    self.disconnect_button = self.button("Desligar", self.disconnect_adapter, QStyle.StandardPixmap.SP_DialogCancelButton)
    buttons.addWidget(self.connect_button)
    buttons.addWidget(self.disconnect_button)
    buttons.addStretch()
    parameters.body.addLayout(buttons)
    layout.addWidget(Columns([parameters, status]))
    layout.addStretch()
    self.kind.currentTextChanged.connect(self.update_controls)
    def show_transport(value):
        for button in self.transport_choices:
            button.setChecked(button.text() == value)
            button.setIcon(icon("cable", "#FFFFFF" if button.isChecked() else "#005C55"))
        for widget in (self.host, self.port):
            widget.setVisible(value == "TCP")
            form.labelForField(widget).setVisible(value == "TCP")
        for widget in (serial_row, self.baud):
            widget.setVisible(value != "TCP")
            form.labelForField(widget).setVisible(value != "TCP")
    self.kind.currentTextChanged.connect(show_transport)
    show_transport(self.kind.currentText())
