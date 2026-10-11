from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication
from scanner_outo.ui.design import ASSETS, COLORS, font, load_fonts

STYLESHEET = """
QWidget { color: #0B1C30; font-family: Inter; font-size: 13px; }
QMainWindow, QDialog, QScrollArea, QWidget#page { background: #F8F9FF; }
QLabel { background: transparent; }
QLabel[role="secondary"] { color: #3E4947; font-size: 12px; }
QLabel[role="title"] { font-size: 28px; font-weight: 600; }
QLabel[role="section"] { font-size: 20px; font-weight: 600; }
QLabel[role="subtitle"] { font-size: 16px; font-weight: 600; }
QLabel[role="metric"] { font-family: 'JetBrains Mono'; font-size: 20px; font-weight: 600; }
QLabel[role="technical"], QPlainTextEdit { font-family: 'JetBrains Mono'; font-size: 11px; }
QPlainTextEdit[role="body"] { font-family: Inter; font-size: 13px; }
QFrame[panel="true"] { background: #FFFFFF; border: 1px solid #E5EEFF; border-radius: 8px; }
QFrame#header { background: #FFFFFF; border-bottom: 1px solid #E5EEFF; }
QFrame#sidebar { background: #213145; }
QFrame#sidebar QLabel { color: #EAF1FF; }
QFrame#sidebar QLabel[role="secondary"] { color: #9CF2E8; }
QPushButton { background: #E5EEFF; color: #0B1C30; border: 2px solid transparent;
    border-radius: 4px; padding: 6px 12px; min-height: 20px; font-weight: 600; }
QPushButton:hover { background: #DCE9FF; border-color: #BDC9C6; }
QPushButton:pressed { background: #BDC9C6; }
QPushButton:focus, QToolButton:focus, QCheckBox:focus { border: 2px solid #0F766E; }
QPushButton[variant="primary"] { background: #0F766E; color: #FFFFFF; }
QPushButton[variant="primary"]:hover { background: #005C55; }
QPushButton[variant="danger"] { background: #FFDAD6; color: #93000A; }
QPushButton[variant="danger"]:hover { border-color: #BA1A1A; }
QPushButton:disabled { color: #3E4947; background: #E5EEFF; border-color: #BDC9C6; }
QPushButton[nav="true"] { text-align: left; background: transparent; color: #EAF1FF;
    padding: 10px 12px; font-weight: 400; border-radius: 4px; }
QPushButton[nav="true"]:checked { background: #0F766E; color: #FFFFFF; border-left: 3px solid #9CF2E8; }
QPushButton[nav="true"]:hover { background: #3E4947; }
QPushButton[nav="true"]:focus { border-color: #9CF2E8; }
QPushButton[choice="true"] { background: #EFF4FF; min-height: 42px; }
QPushButton[choice="true"]:checked { background: #0F766E; color: #FFFFFF; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    background: #EFF4FF; color: #0B1C30; border: 2px solid transparent; border-radius: 4px;
    selection-background-color: #DCE9FF; selection-color: #0B1C30; padding: 6px; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { min-height: 20px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #0F766E; }
QWidget:disabled { color: #3E4947; }
QComboBox QAbstractItemView, QMenu { background: #FFFFFF; color: #0B1C30;
    selection-background-color: #DCE9FF; selection-color: #0B1C30; }
QMenu::item:selected { background: #DCE9FF; }
QCheckBox { spacing: 8px; padding: 4px; border: 2px solid transparent; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #64748B; border-radius: 2px; background: #FFFFFF; }
QCheckBox::indicator:checked { background: #0F766E; border-color: #005C55; }
QTabWidget::pane { border: 0; background: #FFFFFF; }
QTabBar::tab { background: #E5EEFF; padding: 10px 14px; border: 2px solid transparent; }
QTabBar::tab:selected { background: #FFFFFF; color: #005C55; border-bottom-color: #0F766E; }
QTabBar::tab:focus { border-color: #0F766E; }
QTableWidget { background: #FFFFFF; alternate-background-color: #EFF4FF;
    gridline-color: #E5EEFF; border: 1px solid #E5EEFF;
    selection-background-color: #DCE9FF; selection-color: #0B1C30; }
QTableWidget::item { padding: 8px; }
QTableWidget::item:selected { background: #DCE9FF; color: #0B1C30; }
QTableWidget::item:focus { border: 1px solid #0F766E; }
QHeaderView::section { background: #E5EEFF; color: #3E4947; border: 0; padding: 10px; font-size: 11px; font-weight: 600; }
QLabel[badge="neutral"] { background: #E5EEFF; padding: 6px 8px; border-radius: 4px; font-size: 11px; }
QLabel[badge="success"] { background: #0F766E; color: #FFFFFF; padding: 6px 8px; border-radius: 4px; font-size: 11px; }
QLabel[badge="error"] { background: #FFDAD6; color: #93000A; padding: 6px 8px; border-radius: 4px; font-size: 11px; }
QLabel[badge="warning"] { background: #9C573A; color: #FFFFFF; padding: 6px 8px; border-radius: 4px; font-size: 11px; }
QLabel[notice="true"] { background: #EFF4FF; padding: 12px; border-left: 3px solid #0F766E; }
QToolTip { background: #FFFFFF; color: #0B1C30; border: 1px solid #BDC9C6; padding: 6px; }
QStatusBar { background: #EFF4FF; font-size: 11px; }
QScrollArea { border: 0; }
QScrollBar:vertical { background: #EFF4FF; width: 10px; }
QScrollBar::handle:vertical { background: #BDC9C6; min-height: 28px; border-radius: 4px; }
"""

STYLESHEET += '\nQCheckBox::indicator:checked { image: url("' + (ASSETS / "icons/check.svg").as_posix() + '"); }\n'

def apply_theme(app: QApplication) -> None:
    load_fonts()
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")
    if app.font() != font():
        app.setFont(font())
    palette = QPalette()
    for role, token in {
        QPalette.ColorRole.Window: "base", QPalette.ColorRole.WindowText: "text",
        QPalette.ColorRole.Base: "card", QPalette.ColorRole.AlternateBase: "work",
        QPalette.ColorRole.Text: "text", QPalette.ColorRole.Button: "surface",
        QPalette.ColorRole.ButtonText: "text", QPalette.ColorRole.Highlight: "selection",
        QPalette.ColorRole.HighlightedText: "text", QPalette.ColorRole.ToolTipBase: "card",
        QPalette.ColorRole.ToolTipText: "text", QPalette.ColorRole.PlaceholderText: "secondary",
    }.items():
        palette.setColor(role, QColor(COLORS[token]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(COLORS["secondary"]))
    if app.palette() != palette:
        app.setPalette(palette)
    if app.styleSheet() != STYLESHEET:
        app.setStyleSheet(STYLESHEET)
