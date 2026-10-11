from PySide6.QtCore import QSize, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QButtonGroup
from scanner_outo.ui.components import PageStack, Badge, label
from scanner_outo.ui.design import icon

NAVIGATION = ((6, "Visão geral", "dashboard"), (0, "Ligação", "cable"),
              (2, "Diagnóstico", "warning"), (1, "Dados ao vivo", "query_stats"),
              (3, "Análise com IA", "smart_toy"), (4, "Histórico", "history"),
              (5, "Simulador local", "science"))


class Shell(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        rail = QVBoxLayout(self.sidebar)
        rail.setContentsMargins(12, 20, 12, 16)
        rail.setSpacing(8)
        self.sidebar_toggle = QPushButton(icon("menu", "#EAF1FF"), "")
        self.sidebar_toggle.setProperty("nav", True)
        self.sidebar_toggle.setFixedSize(48, 40)
        self.sidebar_toggle.setIconSize(QSize(20, 20))
        self.sidebar_toggle.clicked.connect(self.toggle_sidebar)
        rail.addWidget(self.sidebar_toggle)
        self.brand = label("DANGO\nAUTO DIAGNOSTICS", "subtitle")
        rail.addWidget(self.brand)
        self.link = label("Scanner desligado", "secondary")
        rail.addWidget(self.link)
        rail.addSpacing(16)
        self.navigation = {}
        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        for index, title, symbol in NAVIGATION:
            button = QPushButton(icon(symbol, "#EAF1FF"), title)
            button.setIconSize(QSize(20, 20))
            button.setCheckable(True)
            self.navigation_group.addButton(button)
            button.setProperty("nav", True)
            button.setToolTip(title)
            button.setAccessibleName(title)
            button.clicked.connect(lambda checked=False, target=index: window.tabs.setCurrentIndex(target))
            rail.addWidget(button)
            self.navigation[index] = button
        rail.addStretch()
        self.address = label("Sem ligação", "secondary")
        rail.addWidget(self.address)
        self.disconnect = QPushButton(icon("power_settings_new", "#93000A"), "Desligar")
        self.disconnect.setProperty("variant", "danger")
        self.disconnect.setToolTip("Desligar scanner")
        self.disconnect.setAccessibleName("Desligar scanner")
        self.disconnect.clicked.connect(window.disconnect_adapter)
        rail.addWidget(self.disconnect)
        root.addWidget(self.sidebar)
        work = QVBoxLayout()
        work.setContentsMargins(0, 0, 0, 0)
        work.setSpacing(0)
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header_layout = QGridLayout(self.header)
        self.header_layout.setContentsMargins(16, 12, 16, 12)
        self.badges = {key: Badge() for key in ("origin", "scanner", "simulator", "polling", "ecu", "voltage", "mil")}
        work.addWidget(self.header)
        self.title = label("Visão geral", "title")
        self.title.setContentsMargins(24, 24, 24, 16)
        work.addWidget(self.title)
        window.tabs = PageStack()
        work.addWidget(window.tabs, 1)
        root.addLayout(work, 1)
        window.tabs.currentChanged.connect(self.navigate)
        self.compact = None
        self.manual_compact = None
        self.sidebar_animation = QPropertyAnimation(self, b"sidebarWidth", self)
        self.sidebar_animation.setDuration(240)
        self.sidebar_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.sidebar_animation.finished.connect(self.finish_sidebar_animation)
        self.adapt()

    def get_sidebar_width(self):
        return self.sidebar.width()

    def set_sidebar_width(self, width):
        self.sidebar.setFixedWidth(width)

    sidebarWidth = Property(int, get_sidebar_width, set_sidebar_width)

    def toggle_sidebar(self):
        self.manual_compact = not self.compact
        self.set_sidebar_compact(self.manual_compact, animated=True)

    def set_sidebar_compact(self, compact, animated=False):
        if compact == self.compact:
            return
        self.sidebar_animation.stop()
        self.compact = compact
        target = 72 if compact else 260
        name = "Expandir barra lateral" if compact else "Recolher barra lateral"
        self.sidebar_toggle.setToolTip(name)
        self.sidebar_toggle.setAccessibleName(name)
        # Hide labels during the transition so intermediate widths do not clip text.
        self.show_sidebar_labels(False)
        if animated:
            self.sidebar_animation.setStartValue(self.sidebar.width())
            self.sidebar_animation.setEndValue(target)
            self.sidebar_animation.start()
        else:
            self.set_sidebar_width(target)
            self.finish_sidebar_animation()

    def finish_sidebar_animation(self):
        self.show_sidebar_labels(not self.compact)

    def show_sidebar_labels(self, expanded):
        self.brand.setText("DANGO\nAUTO DIAGNOSTICS" if expanded else "DANGO")
        self.brand.setStyleSheet("" if expanded else "font-size: 10px; font-weight: 600;")
        self.link.setVisible(expanded)
        self.address.setVisible(expanded)
        self.disconnect.setText("Desligar" if expanded else "")
        for index, title, _ in NAVIGATION:
            self.navigation[index].setText(title if expanded else "")

    def navigate(self, index):
        for number, button in self.navigation.items():
            button.setChecked(number == index)
        self.title.setText(next(title for number, title, _ in NAVIGATION if number == index))
        if hasattr(self.window, "reading_chart"):
            self.window.reading_chart.refresh()

    def adapt(self):
        columns = 7 if self.width() >= 1300 else 4
        for index, badge in enumerate(self.badges.values()):
            self.header_layout.addWidget(badge, index // columns, index % columns)
        for col in range(7):
            self.header_layout.setColumnStretch(col, 1 if col < columns else 0)
        compact = self.width() < 1050 if self.manual_compact is None else self.manual_compact
        self.set_sidebar_compact(compact)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adapt()
