from __future__ import annotations

from datetime import datetime, timezone
import json
import http.client
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QTableWidget

from scanner_outo.config import Settings
from scanner_outo.gemini import SYSTEM_INSTRUCTION
from scanner_outo.models import AVAILABLE, COMPLETE, EMPTY_CODES, ConnectionConfig, origin_label
from scanner_outo.services import DiagnosticService
from scanner_outo.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scenarios.rough_idle import COOLANT_C, RPM_SEQUENCE, SYMPTOMS
from scripts.emulator_environment import find_emulator_python


class FaultScenarioTests(unittest.TestCase):
    """TCP real para o pacote ELM instalado; Gemini sempre substituido."""

    port_override = None
    require_emulator = False

    @classmethod
    def setUpClass(cls):
        configured = os.getenv("ELM327_PYTHON")
        interpreter = find_emulator_python(ROOT)
        if interpreter is None:
            message = "Defina ELM327_PYTHON com o Python que tem ELM327-emulator 4.0.0."
            if cls.require_emulator or configured:
                raise RuntimeError(message)
            raise unittest.SkipTest(message)
        cls.interpreter = interpreter
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", cls.port_override or 0))
            cls.port = probe.getsockname()[1]
        cls.process = subprocess.Popen(
            [str(interpreter), "-X", "utf8", "-u", str(ROOT / "scripts/run_fault_emulator.py"),
             "--port", str(cls.port), "--stop-after", "120"],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            text=True, encoding="utf-8", errors="replace",
        )
        cls.output = []
        cls.control_info = None
        cls.ready = threading.Event()

        def read_output():
            for line in cls.process.stdout:
                cls.output.append(line)
                if line.startswith("CONTROL "):
                    cls.control_info = json.loads(line[8:])
                if "READY ELM327-emulator 4.0.0" in line:
                    cls.ready.set()

        cls.reader = threading.Thread(target=read_output, daemon=True)
        cls.reader.start()
        cls.addClassCleanup(cls.stop_emulator)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if cls.ready.is_set():
                return
            if cls.process.poll() is not None:
                cls.reader.join(timeout=2)
                raise RuntimeError("Launcher falhou: " + "".join(cls.output))
            time.sleep(0.05)
        raise RuntimeError("O launcher nao ficou pronto no prazo.")

    @classmethod
    def stop_emulator(cls):
        if cls.process.poll() is None:
            try:
                if cls.control_info:
                    connection = http.client.HTTPConnection("127.0.0.1", cls.control_info["port"], timeout=2)
                    try:
                        connection.request("POST", "/control", json.dumps({"action": "shutdown"}), {"Authorization": "Bearer " + cls.control_info["token"]})
                        connection.getresponse().read()
                    finally:
                        connection.close()
                else:
                    cls.process.terminate()
            except (OSError, http.client.HTTPException):
                cls.process.terminate()
        try:
            cls.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait(timeout=5)
        cls.reader.join(timeout=2)
        cls.process.stdout.close()

    def test_launcher_refuses_occupied_port(self):
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen(1)
            result = subprocess.run(
                [str(self.interpreter), str(ROOT / "scripts/run_fault_emulator.py"),
                 "--port", str(occupied.getsockname()[1]), "--stop-after", "1"],
                cwd=ROOT, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("ocupada/indisponivel", result.stderr)
            self.assertGreaterEqual(occupied.fileno(), 0)

    def test_common_launcher_from_other_directory(self):
        with tempfile.TemporaryDirectory() as temp, socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
            probe.close()
            result = subprocess.run(
                [sys.executable, "-X", "utf8", str(ROOT / "scripts/run_emulator.py"),
                 "--port", str(port), "--stop-after", "1"],
                cwd=temp, env={**os.environ, "ELM327_PYTHON": str(self.interpreter)},
                capture_output=True, text=True, encoding="utf-8", timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"car em 127.0.0.1:{port}", result.stdout)
            self.assertIn(f"elm-{port}.log", result.stdout)
            self.assertTrue((ROOT / f"logs/emulator/elm-{port}.log").is_file())
            self.assertFalse((Path(temp) / "elm.log").exists())

    def assert_recent(self, readings):
        self.assertEqual(len(readings), 12)
        readings = [r for r in readings if r["value"] is not None]
        self.assertEqual(len(readings), 3)
        for reading in readings:
            self.assertEqual(reading["status"], AVAILABLE)
            self.assertFalse(reading["stale"])
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(reading["timestamp"])).total_seconds()
            self.assertGreaterEqual(age, 0)
            self.assertLess(age, 10)

    def test_obd_requests_and_decoding(self):
        service = DiagnosticService()
        self.addCleanup(service.disconnect)
        with self.assertLogs("scanner_outo", level="INFO") as trace:
            service.connect(ConnectionConfig(port=self.port, simulation=True))
            values = []
            for _ in range(len(RPM_SEQUENCE) * 2):
                snapshot = service.poll()
                readings = {r["pid"]: r for r in snapshot["readings"]}
                values.append(readings["0C"]["value"])
                self.assertEqual(readings["05"]["value"], COOLANT_C)
                self.assertEqual(readings["0D"]["value"], 0)
            offset = RPM_SEQUENCE.index(values[0])
            self.assertEqual(values, [RPM_SEQUENCE[(offset + i) % len(RPM_SEQUENCE)] for i in range(len(values))])
            codes = service.read_codes()
            self.assertEqual([(c["code"], c["status"], c["ecu"]) for c in codes["codes"]], [("P0301", "Confirmado", "7E8")])
            self.assertEqual(codes["code_queries"]["Confirmado"]["status"], COMPLETE)
            self.assertEqual(codes["code_queries"]["Pendente"]["status"], EMPTY_CODES)
            freeze = service.read_freeze_frame()
            self.assertEqual(freeze["freeze_codes"], {"7E8": ["P0301"]})
            self.assertEqual(freeze["freeze_status"], COMPLETE)
            self.assertEqual(len(freeze["freeze_frame"]), 12)
            self.assertEqual({r["pid"]: r["value"] for r in freeze["freeze_frame"] if r["pid"] in ("0C", "05", "0D")}, {"0C": 710, "05": 88, "0D": 0})
            unsupported = service.client.send("0112").response
            self.assertIn("NO DATA", unsupported)
            mil = service.client.send("0101").response
            self.assertIn("41 01 81", mil)
        obd_log = "\n".join(trace.output)
        self.assertIn("pedido=03", obd_log)
        self.assertIn("43 03 01", obd_log)
        self.assertNotIn("pedido=04", obd_log)
        print(next(line for line in trace.output if "pedido=03" in line))
        print(f"TCP 127.0.0.1:{self.port}: descodificado P0301 confirmado, ECU 7E8")
        print(f"RPM recebidos: {values}; temperatura={COOLANT_C}; velocidade=0")

    def test_gui_gemini_save_open_export(self):
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        # Nunca carrega .env: credencial ficticia e transporte Gemini substituido.
        settings = Settings(data_dir=Path(temp.name), api_key="ficticia-sem-acesso-remoto", model="cliente-simulado")
        with patch("scanner_outo.gemini.official_generate", side_effect=AssertionError("Chamadas reais proibidas")) as remote:
            window = MainWindow(settings)

            def wait():
                deadline = time.monotonic() + 15
                idle_since = None
                while time.monotonic() < deadline:
                    QTest.qWait(20)
                    if any(window.busy.values()):
                        idle_since = None
                    elif idle_since is None:
                        idle_since = time.monotonic()
                    elif time.monotonic() - idle_since >= 0.15:
                        return
                self.fail("Workers nao terminaram: " + window.last_error)

            def close_window():
                window.close()
                wait()

            self.addCleanup(close_window)

            window.show()
            wait()
            window.port.setValue(self.port)
            window.connect_button.click()
            wait()
            self.assertEqual(window.state["adapter_status"], "Ligado", window.last_error)
            window.read_codes()
            wait()
            window.read_freeze()
            wait()
            window.read_button.click()
            wait()
            self.assert_recent(window.snapshot()["readings"])
            self.assertEqual(window.codes_table.rowCount(), 1)
            self.assertEqual(window.codes_table.item(0, 0).text(), "P0301")
            self.assertEqual(window.codes_table.item(0, 2).text(), "Confirmado")
            self.assertTrue(window.state["simulation"])
            self.assertIn(origin_label(True), window.connection_status.text())
            window.symptoms.setPlainText(SYMPTOMS)
            calls = []

            def simulated_generate(_settings, model, payload):
                self.assertEqual(model, "cliente-simulado")
                self.assertEqual(payload["origem"], origin_label(True))
                self.assertEqual(payload["sintomas"], SYMPTOMS)
                self.assertEqual(payload["codigos"][0]["code"], "P0301")
                self.assert_recent(payload["parametros"])
                self.assertNotIn("connection", payload)
                self.assertIn("nao identifica por si so uma peca", SYSTEM_INSTRUCTION)
                calls.append(payload)
                response = {
                    "factos_medidos": ["Dados simulados: P0301 confirmado, motor quente e veiculo parado."],
                    "hipoteses": ["Possivel problema de ignicao, alimentacao ou compressao; P0301 nao identifica uma peca especifica."],
                    "evidencias": ["P0301 descreve falha de combustao no cilindro 1; sintomas relatam ralenti irregular."],
                    "informacao_em_falta": ["Faltam testes de ignicao, injector e compressao para confirmar a causa."],
                    "proximos_testes": ["Inspeccionar ignicao e ligacoes; testar alimentacao e compressao antes de substituir componentes."],
                }
                return {"text": json.dumps(response), "tokens": {"total": 100}}

            window.gemini.generate = simulated_generate
            window.tabs.setCurrentIndex(3)
            window.analyze_button.click()
            wait()
            self.assertEqual(len(calls), 1)
            self.assertIn("nao identifica uma peca especifica", window.ai_output.toPlainText())
            self.assertIn("proximos_testes", window.state["analysis"]["result"])
            artifact = ROOT / "artifacts"
            artifact.mkdir(exist_ok=True)
            self.assertTrue(window.grab().save(str(artifact / "fault-p0301-ai.png")))
            window.tabs.setCurrentIndex(2)
            self.assertTrue(window.grab().save(str(artifact / "fault-p0301-codes.png")))
            window.save_button.click()
            wait()
            window.refresh_history()
            wait()
            self.assertEqual(len(window.history_rows), 1)
            window.history_table.selectRow(0)
            session_id = window.selected_session_id()
            saved = window.store.load(session_id)
            self.assertEqual(saved["codes"][0]["code"], "P0301")
            self.assertEqual(saved["analysis_input"], calls[0])
            window.open_button.click()
            wait()
            dialogs = [d for d in window.findChildren(QDialog) if d.isVisible()]
            self.assertEqual(len(dialogs), 1)
            tables = dialogs[0].findChildren(QTableWidget)
            self.assertTrue(any(t.rowCount() and t.item(0, 0).text() == "P0301" for t in tables))
            dialogs[0].close()
            destination = Path(temp.name) / "fault-session.json"
            with patch("scanner_outo.ui.main_window.QFileDialog.getSaveFileName", return_value=(str(destination), "JSON")):
                window.export_button.click()
                wait()
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), saved)
            window.tabs.setCurrentIndex(3)
            window.analyze_button.click()
            wait()
            self.assertEqual(len(calls), 1)
            self.assertTrue(window.state["analysis"]["cache"])
            remote.assert_not_called()
            window.disconnect_button.click()
            wait()
            self.assertTrue(all(r["stale"] for r in window.snapshot()["readings"] if r["value"] is not None))
            window.close()
            wait()
        print("GUI: P0301 via OBD, leituras recentes, sintomas, Gemini simulado, cache, guardar/abrir/exportar e desactualizacao aprovados.")


if __name__ == "__main__":
    unittest.main()
