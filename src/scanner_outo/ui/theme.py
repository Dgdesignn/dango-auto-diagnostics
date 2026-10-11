from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


STYLESHEET = """
QMainWindow, QDialog, QWidget { color: #202b33; }
QMainWindow, QDialog { background: #f4f6f8; }
QLabel { color: #202b33; background: transparent; }
QLabel:disabled { color: #596674; }
QPushButton {
    color: #202b33; background: #ffffff; border: 2px solid #aab6c0;
    border-radius: 4px; padding: 7px 12px;
}
QPushButton:hover { background: #edf6f5; border-color: #006c67; }
QPushButton:pressed { background: #d1e8e6; }
QPushButton:focus { border-color: #006c67; }
QPushButton:disabled { color: #596674; background: #e8edf1; border-color: #bcc6cf; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {
    color: #202b33; background: #ffffff; border: 2px solid #aab6c0;
    border-radius: 3px; selection-background-color: #006c67; selection-color: #ffffff;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { min-height: 26px; padding: 2px 5px; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {
    border-color: #006c67;
}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    color: #596674; background: #e8edf1; border-color: #bcc6cf;
}
QComboBox QAbstractItemView {
    color: #202b33; background: #ffffff; selection-color: #ffffff;
    selection-background-color: #006c67; border: 1px solid #aab6c0;
}
QTabWidget::pane { border: 1px solid #ccd3da; background: #ffffff; }
QTabBar::tab { color: #202b33; background: #e8edf1; padding: 9px 14px; border: 2px solid transparent; }
QTabBar::tab:selected { color: #004b47; background: #ffffff; border-bottom-color: #006c67; }
QTabBar::tab:focus { border-color: #006c67; }
QTabBar::tab:disabled { color: #596674; }
QTableWidget {
    color: #202b33; background: #ffffff; alternate-background-color: #f0f4f6;
    gridline-color: #ccd3da; selection-background-color: #006c67; selection-color: #ffffff;
}
QTableWidget::item:selected { color: #ffffff; background: #006c67; }
QTableWidget::item:focus { border: 1px solid #004b47; }
QHeaderView::section { color: #202b33; background: #e8edf1; padding: 5px; border: 1px solid #ccd3da; }
QStatusBar { color: #202b33; background: #f4f6f8; }
QToolTip { color: #202b33; background: #ffffff; border: 1px solid #aab6c0; }
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: "#f4f6f8", QPalette.ColorRole.WindowText: "#202b33",
        QPalette.ColorRole.Base: "#ffffff", QPalette.ColorRole.AlternateBase: "#f0f4f6",
        QPalette.ColorRole.Text: "#202b33", QPalette.ColorRole.Button: "#ffffff",
        QPalette.ColorRole.ButtonText: "#202b33", QPalette.ColorRole.Highlight: "#006c67",
        QPalette.ColorRole.HighlightedText: "#ffffff", QPalette.ColorRole.ToolTipBase: "#ffffff",
        QPalette.ColorRole.ToolTipText: "#202b33", QPalette.ColorRole.PlaceholderText: "#596674",
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#596674"))
    for role in (QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#e8edf1"))
    app.setPalette(palette)
