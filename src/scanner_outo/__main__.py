from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from scanner_outo.config import Settings, configure_logging
from scanner_outo.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Scanner Outo")
    app.setOrganizationName("Daniel Geraldo")
    try:
        settings = Settings.load()
        configure_logging(settings)
        window = MainWindow(settings)
    except Exception:
        QMessageBox.critical(None, "Configuração", "Não foi possivel iniciar. Verifique a configuração e permissões da pasta de dados.")
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
