"""Validacao Qt real de leitura; nunca envia o comando 04."""
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root / "tests"))

from test_ui import GuiTests

if __name__ == "__main__":
    GuiTests.real_emulator = "--real" in sys.argv
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuiTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
