from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QScrollArea, QStackedWidget)


def label(text, role=None):
    result = QLabel(text)
    result.setWordWrap(True)
    if role:
        result.setProperty("role", role)
    return result


def polish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Badge(QLabel):
    def __init__(self, text="", state="neutral"):
        super().__init__(text)
        self.setWordWrap(True)
        self.setProperty("badge", state)

    def update_state(self, text, state="neutral"):
        self.setText(text)
        self.setProperty("badge", state)
        polish(self)


class Panel(QFrame):
    def __init__(self, title=None):
        super().__init__()
        self.setProperty("panel", True)
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(16, 16, 16, 16)
        self.body.setSpacing(16)
        self.body.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)
        if title:
            self.body.addWidget(label(title, "subtitle"))


class ReadingCard(Panel):
    def __init__(self, title, symbol):
        super().__init__()
        from scanner_outo.ui.design import icon
        row = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(icon(symbol).pixmap(24, 24))
        row.addWidget(mark)
        row.addWidget(label(title, "secondary"), 1)
        self.body.addLayout(row)
        self.value = label("--", "metric")
        self.detail = label("Não consultado", "secondary")
        self.body.addWidget(self.value)
        self.body.addWidget(self.detail)
        self.setMinimumHeight(126)


class Columns(QWidget):
    """Reflow without duplicating widgets, timers or signal connections."""
    def __init__(self, widgets, breakpoint=760, maximum=2):
        super().__init__()
        self.items = widgets
        self.breakpoint = breakpoint
        self.maximum = maximum
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)
        self.grid.setSizeConstraint(QGridLayout.SizeConstraint.SetMinimumSize)
        self.columns = None
        self.reflow()

    def reflow(self):
        count = 2 if self.width() >= self.breakpoint else 1
        if self.maximum == 3:
            count = 3 if self.width() >= self.breakpoint else (2 if self.width() >= 480 else 1)
        if self.maximum == 4 and self.width() >= 1000:
            count = 4
        if count == self.columns:
            return
        self.columns = count
        for index, widget in enumerate(self.items):
            self.grid.addWidget(widget, index // count, index % count)
        for col in range(self.maximum):
            self.grid.setColumnStretch(col, 1 if col < count else 0)
        self.grid.invalidate()
        self.updateGeometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow()


class TechnicalSection(QWidget):
    def __init__(self, title, content):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        toggle = QPushButton(title)
        from scanner_outo.ui.design import icon
        toggle.setIcon(icon("settings"))
        toggle.setCheckable(True)
        toggle.setToolTip(title)
        toggle.toggled.connect(content.setVisible)
        content.hide()
        layout.addWidget(toggle)
        layout.addWidget(content)
        self.toggle = toggle


class PageStack(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.pages = {}

    def addTab(self, page, title):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        self.pages[page] = scroll
        return self.addWidget(scroll)

    def setCurrentWidget(self, page):
        super().setCurrentWidget(self.pages.get(page, page))
