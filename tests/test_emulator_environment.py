import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.emulator_environment import emulator_log_handler, find_emulator_python


class EmulatorEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "projecto com espacos"
        self.root.mkdir()

    def executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path.resolve()

    def test_sibling_environment(self):
        relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
        expected = self.executable(self.root.parent / "simulador_scanner/.venv" / relative)
        self.assertEqual(find_emulator_python(self.root, {}), expected)

    def test_explicit_override(self):
        expected = self.executable(self.root / "outro ambiente/python.exe")
        self.assertEqual(find_emulator_python(self.root, {"ELM327_PYTHON": str(expected)}), expected)

    def test_relative_override_uses_project_not_cwd(self):
        expected = self.executable(self.root / "ambiente/python.exe")
        self.assertEqual(find_emulator_python(self.root, {"ELM327_PYTHON": "ambiente/python.exe"}), expected)

    def test_invalid_override_does_not_silently_fallback(self):
        with self.assertRaisesRegex(FileNotFoundError, "ELM327_PYTHON"):
            find_emulator_python(self.root, {"ELM327_PYTHON": "nao-existe/python.exe"})

    def test_current_python_with_emulator(self):
        with patch("scripts.emulator_environment.importlib.util.find_spec", return_value=object()):
            self.assertEqual(find_emulator_python(self.root, {}), Path(sys.executable).resolve())

    def test_missing_environment(self):
        with patch("scripts.emulator_environment.importlib.util.find_spec", return_value=None):
            self.assertIsNone(find_emulator_python(self.root, {}))

    def test_logging_template_appends_and_rotates(self):
        config = json.loads((ROOT / "config/elm-logging.json").read_text(encoding="utf-8"))
        handler = config["handlers"]["file"]
        self.assertEqual(handler["()"], "scripts.emulator_environment.emulator_log_handler")
        self.assertEqual(handler["mode"], "a")
        self.assertGreater(handler["maxBytes"], 0)
        self.assertGreater(handler["backupCount"], 0)

    def test_log_handler_uses_absolute_destination_and_appends(self):
        path = self.root / "emulator.log"
        path.write_text("anterior\n", encoding="utf-8")
        with patch.dict(os.environ, {"SCANNER_EMULATOR_LOG_FILE": str(path)}):
            handler = emulator_log_handler("unused.log", mode="a", maxBytes=1000, backupCount=2, encoding="utf-8")
        handler.close()
        self.assertEqual(Path(handler.baseFilename), path)
        self.assertEqual(path.read_text(encoding="utf-8"), "anterior\n")
