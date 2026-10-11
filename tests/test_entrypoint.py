import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class EntrypointTests(unittest.TestCase):
    def test_run_app_opens_and_closes_cleanly(self):
        code = '''
import runpy
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow
original_exec = QApplication.exec
def bounded_exec(self):
    windows = [w for w in self.topLevelWidgets() if isinstance(w, QMainWindow) and w.isVisible()]
    assert windows, "A janela principal nao abriu"
    QTimer.singleShot(300, windows[0].close)
    return original_exec()
QApplication.exec = bounded_exec
runpy.run_path("scripts/run_app.py", run_name="__main__")
'''
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "SCANNER_DATA_DIR": temp, "GEMINI_DAILY_LIMIT": "10", "GEMINI_MIN_INTERVAL": "30"}
            process = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertNotIn("Traceback", process.stderr)
