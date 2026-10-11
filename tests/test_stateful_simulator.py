from __future__ import annotations

import http.client
import json
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

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

from scanner_outo.communication.base import TransportError
from scanner_outo.config import Settings
from scanner_outo.models import ConnectionConfig, EMPTY_CODES, UNAVAILABLE
from scanner_outo.services import DiagnosticService
from scanner_outo.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scenarios.vehicle import VehicleState
from scripts.emulator_environment import find_emulator_python


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RunningSimulator:
    def __init__(self, scenario, loss=12):
        self.port = free_port()
        self.ready = threading.Event()
        self.info = None
        self.output = []
        self.process = subprocess.Popen(
            [str(find_emulator_python()), "-X", "utf8", "-u", str(ROOT / "scripts/run_fault_emulator.py"),
             "--scenario", scenario, "--port", str(self.port), "--loss-after-requests", str(loss),
             "--stop-after", "90"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            text=True, encoding="utf-8", env={key: val for key, val in os.environ.items()
                                           if key not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")})
        def read():
            for line in self.process.stdout:
                self.output.append(line)
                if line.startswith("CONTROL "):
                    self.info = json.loads(line[8:])
                    self.ready.set()
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        if not self.ready.wait(10):
            self.close()
            raise RuntimeError(f"Launcher nao iniciou (exit={self.process.returncode}, python={find_emulator_python()}): " + "".join(self.output))

    def control(self, action, token=None, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.info["port"], timeout=3)
        try:
            connection.request("POST", "/control", json.dumps(payload if payload is not None else {"action": action}),
                               {"Authorization": "Bearer " + (token or self.info["token"])})
            response = connection.getresponse()
            content = response.read(8192)
            return response.status, json.loads(content) if response.status == 200 else None
        finally:
            connection.close()

    def close(self):
        if self.process.stdout.closed:
            return
        if self.process.poll() is None:
            try:
                if self.info:
                    self.control("shutdown")
                else:
                    self.process.terminate()
                self.process.wait(7)
            except (OSError, subprocess.TimeoutExpired, http.client.HTTPException):
                self.process.kill()
                self.process.wait(5)
        self.reader.join(2)
        self.process.stdout.close()


class VehicleStateTests(unittest.TestCase):
    def test_clear_does_not_repair_and_readings_do_not_advance_cycles(self):
        state = VehicleState("rough_idle_p0301")
        self.assertIn("44", state.response("04"))
        for _ in range(20):
            state.response("010C")
            state.response("03")
        cleared = state.snapshot()
        self.assertEqual(cleared["active_causes"], ["P0301"])
        self.assertFalse(cleared["confirmed"])
        self.assertFalse(cleared["pending"])
        self.assertFalse(cleared["mil"])
        self.assertIsNone(cleared["freeze"])
        self.assertEqual(cleared["monitors"], {"misfire": "incomplete"})
        self.assertEqual(cleared["cycles"], 0)
        self.assertEqual(state.control("cycle")["pending"], ["P0301"])
        self.assertFalse(state.snapshot()["mil"])
        confirmed = state.control("cycle")
        self.assertEqual(confirmed["confirmed"], ["P0301"])
        self.assertTrue(confirmed["mil"])
        self.assertEqual(confirmed["freeze"]["code"], "P0301")

    def test_resolve_clear_cycles_and_reset(self):
        state = VehicleState("rough_idle_p0301")
        state.control("resolve")
        self.assertEqual(state.snapshot()["confirmed"], ["P0301"])
        state.response("04")
        for _ in range(4):
            self.assertFalse(state.control("cycle")["confirmed"])
        self.assertEqual(state.snapshot()["rpm"], 750)
        self.assertEqual(state.control("reset")["confirmed"], ["P0301"])

    def test_isolation_and_snapshot_copy(self):
        a, b = VehicleState("rough_idle_p0301"), VehicleState("rough_idle_p0301")
        a.response("04")
        a.control("resolve")
        a.snapshot()["active_causes"].append("P0420")
        self.assertEqual(b.snapshot()["confirmed"], ["P0301"])
        self.assertFalse(a.snapshot()["active_causes"])


class StatefulTcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if find_emulator_python() is None:
            raise unittest.SkipTest("ELM327-emulator nao encontrado.")

    def simulator(self, scenario, loss=12):
        simulator = RunningSimulator(scenario, loss)
        self.addCleanup(simulator.close)
        return simulator

    def service(self, simulator):
        service = DiagnosticService()
        self.addCleanup(service.disconnect)
        service.connect(ConnectionConfig(port=simulator.port, timeout=1))
        return service

    def test_healthy_and_multiple_dtcs(self):
        for scenario in ("healthy", "multiple_dtcs"):
            with self.subTest(scenario=scenario):
                simulator = self.simulator(scenario)
                service = self.service(simulator)
                readings = {r["pid"]: r["value"] for r in service.poll()["readings"]}
                self.assertEqual(readings["05"], 88)
                self.assertEqual(readings["0D"], 0)
                codes = service.read_codes()
                status = service.query("0101")[0].data
                if scenario == "healthy":
                    self.assertEqual(readings["0C"], 750)
                    self.assertFalse(codes["codes"])
                    self.assertTrue(all(q["status"] == EMPTY_CODES for q in codes["code_queries"].values()))
                    self.assertEqual(status[2], 0)
                else:
                    self.assertEqual([(c["code"], c["status"]) for c in codes["codes"]],
                                     [("P0300", "Confirmado"), ("P0171", "Confirmado"), ("P0302", "Pendente")])
                    self.assertEqual(status[2], 0x82)
                service.disconnect()
                simulator.close()

    def test_no_data_is_not_empty_codes(self):
        service = self.service(self.simulator("no_data"))
        self.assertEqual(service.session.adapter_status, "Ligado")
        self.assertIn("OK", service.client.send("ATE0").response.upper())
        snapshot = service.read_codes()
        self.assertTrue(all(q["status"] == UNAVAILABLE for q in snapshot["code_queries"].values()))
        self.assertFalse(snapshot["codes"])
        self.assertEqual(service.read_freeze_frame()["freeze_status"], UNAVAILABLE)

    def test_full_clear_cycle_repair_reset_over_obd(self):
        simulator = self.simulator("rough_idle_p0301")
        service = self.service(simulator)
        self.assertEqual(service.read_codes()["codes"][0]["code"], "P0301")
        self.assertEqual(service.read_freeze_frame()["freeze_codes"], {"7E8": ["P0301"]})
        initial = service.query("0101")[0].data
        self.assertEqual(initial[2:4], bytes([0x81, 1]))
        service.client.send("ATH0")
        service.client.send("ATS0")
        self.assertIn("44", service.client.send("04").response)
        self.assertNotIn("7E8", service.client.send("03").response)
        service.client.enable_headers()
        service.client.send("ATS1")
        with self.assertLogs("scanner_outo", level="INFO") as trace:
            cleared = service.clear_codes()
        self.assertTrue(any("7E8 01 44" in line for line in trace.output))
        self.assertFalse(cleared["codes"])
        self.assertIn("releitura confirmadas", cleared["clear_status"])
        self.assertEqual(service.query("0101")[0].data[2:4], bytes([0, 0x11]))
        self.assertEqual(service.read_freeze_frame()["freeze_status"], UNAVAILABLE)
        self.assertEqual(simulator.control("status")[1]["state"]["active_causes"], ["P0301"])
        for _ in range(3):
            service.poll()
        self.assertFalse(service.read_codes()["codes"])
        simulator.control("cycle")
        self.assertEqual([(c["code"], c["status"]) for c in service.read_codes()["codes"]], [("P0301", "Pendente")])
        self.assertEqual(service.query("0101")[0].data[2:4], bytes([0, 1]))
        simulator.control("cycle")
        self.assertEqual(service.read_codes()["codes"][0]["status"], "Confirmado")
        self.assertEqual(service.read_freeze_frame()["freeze_codes"], {"7E8": ["P0301"]})
        simulator.control("resolve")
        service.clear_codes()
        simulator.control("cycle")
        simulator.control("cycle")
        self.assertFalse(service.read_codes()["codes"])
        self.assertFalse(simulator.control("status")[1]["state"]["mil"])
        simulator.control("reset")
        self.assertEqual(service.read_codes()["codes"][0]["code"], "P0301")

    def test_clear_multiple_and_isolation_two_real_instances(self):
        a, b = self.simulator("multiple_dtcs"), self.simulator("rough_idle_p0301")
        sa, sb = self.service(a), self.service(b)
        sa.clear_codes()
        self.assertFalse(sa.read_codes()["codes"])
        self.assertIsNone(a.control("status")[1]["state"]["freeze"])
        self.assertEqual(sb.read_codes()["codes"][0]["code"], "P0301")
        self.assertTrue(b.control("status")[1]["state"]["mil"])

    def test_control_validation_and_graceful_shutdown(self):
        simulator = self.simulator("healthy")
        self.assertEqual(simulator.control("status", token="invalido")[0], 403)
        self.assertEqual(simulator.control("status", payload={"action": "status", "command": "04"})[0], 400)
        self.assertEqual(simulator.control("execute")[0], 400)
        self.assertEqual(simulator.control("status", payload=["status"])[0], 400)
        self.assertEqual(simulator.control("status")[0], 200)
        simulator.close()
        self.assertEqual(simulator.process.returncode, 0)

    def test_manual_control_launcher(self):
        simulator = self.simulator("rough_idle_p0301")
        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "scripts/control_emulator.py"), "resolve",
             "--port", str(simulator.info["port"]), "--token", simulator.info["token"]],
            capture_output=True, text=True, timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)["state"]
        self.assertFalse(state["active_causes"])
        self.assertEqual(state["confirmed"], ["P0301"])

    def test_connection_loss_marks_values_stale_and_reset_recovers(self):
        simulator = self.simulator("connection_loss", loss=4)
        service = self.service(simulator)
        self.assertEqual(len([r for r in service.poll()["readings"] if r["value"] is not None]), 3)
        with self.assertRaises(TransportError):
            service.poll()
        snapshot = service.session.to_dict()
        self.assertEqual(snapshot["adapter_status"], "Desligado")
        self.assertTrue(all(r["stale"] for r in snapshot["readings"]))
        self.assertTrue(simulator.control("status")[1]["state"]["loss_latched"])
        simulator.control("reset")
        service.connect(ConnectionConfig(port=simulator.port, timeout=1))
        self.assertEqual(service.poll()["adapter_status"], "Ligado")


class SimulatorGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        if find_emulator_python() is None:
            raise unittest.SkipTest("ELM327-emulator nao encontrado.")

    def setUp(self):
        self.remote = patch("scanner_outo.gemini.official_generate", side_effect=AssertionError("Gemini real proibido"))
        self.remote_mock = self.remote.start()
        self.addCleanup(self.remote.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.window = MainWindow(Settings(data_dir=Path(self.temp.name), api_key=""))
        self.window.show()
        self.addCleanup(self.close_window)
        self.idle()

    def until(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            QTest.qWait(20)
            if predicate():
                return
        self.fail("Timeout GUI: " + self.window.simulator.process_status.text() + " / " + self.window.last_error)

    def idle(self):
        self.until(lambda: not any(self.window.busy.values()) and not self.window.simulator.busy)
        QTest.qWait(150)
        self.until(lambda: not any(self.window.busy.values()) and not self.window.simulator.busy)

    def close_window(self):
        self.window.close()
        self.until(lambda: not self.window.isVisible() and not self.window.simulator.owned)
        self.idle()
        self.remote_mock.assert_not_called()

    def start(self, scenario="rough_idle_p0301", loss=12, as_real=False):
        panel = self.window.simulator
        panel.port.setValue(free_port())
        panel.scenario.setCurrentText(scenario)
        panel.loss_count.setValue(loss)
        panel.start_button.click()
        self.until(lambda: panel.ready)
        self.idle()
        self.window.port.setValue(panel.port.value())
        if as_real:
            self.window.origin.setCurrentIndex(self.window.origin.findData(False))
        self.window.connect_button.click()
        self.idle()
        self.assertIn("Simulador gerido", self.window.connection_status.text())
        self.assertTrue(self.window.state["simulation"])
        self.assertTrue(self.window.state["connection"]["simulation"])

    def test_controls_clear_photo_cycles_reset_and_close(self):
        window, panel = self.window, self.window.simulator
        self.assertEqual(panel.scenario.count(), 6)
        self.assertFalse(panel.cycle_button.isEnabled())
        ticks = []
        timer = QTimer(window)
        timer.timeout.connect(lambda: ticks.append(1))
        timer.start(10)
        self.start(as_real=True)
        window.poll()
        self.idle()
        window.read_codes()
        self.idle()
        self.assertEqual(window.codes_table.item(0, 0).text(), "P0301")
        with patch("scanner_outo.ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes) as confirmation:
            window.clear_button.click()
            self.idle()
            self.until(lambda: "releitura confirmadas" in window.state["clear_status"])
            self.idle()
            self.assertEqual(confirmation.call_args.args[-1], QMessageBox.StandardButton.No)
        self.assertEqual(window.codes_table.rowCount(), 0)
        stored = window.store.list_sessions()
        self.assertEqual(window.store.load(stored[0]["id"])["codes"][0]["code"], "P0301")
        self.assertEqual(panel.vehicle["active_causes"], ["P0301"])
        panel.cycle_button.click()
        self.idle()
        window.read_codes()
        self.idle()
        self.assertEqual(window.codes_table.item(0, 2).text(), "Pendente")
        panel.cycle_button.click()
        self.idle()
        window.read_codes()
        self.idle()
        self.assertEqual(window.codes_table.item(0, 2).text(), "Confirmado")
        panel.resolve_button.click()
        self.idle()
        self.assertFalse(panel.vehicle["active_causes"])
        with patch("scanner_outo.ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            window.clear_button.click()
            self.idle()
            panel.cycle_button.click()
            self.idle()
            window.read_codes()
            self.idle()
            self.assertEqual(window.codes_table.rowCount(), 0)
            old_session = window.state["created_at"]
            panel.reset_button.click()
            self.idle()
            self.until(lambda: panel.vehicle["confirmed"] == ["P0301"])
        self.assertNotEqual(window.state["created_at"], old_session)
        self.assertEqual(window.state["adapter_status"], "Desligado")
        self.assertFalse(window.state["readings"])
        self.assertFalse(window.state["codes"])
        self.assertFalse(window.state["analysis"])
        self.assertGreater(len(ticks), 20)
        window.tabs.setCurrentWidget(panel)
        artifact = ROOT / "artifacts"
        artifact.mkdir(exist_ok=True)
        self.assertTrue(window.grab().save(str(artifact / "stateful-simulator.png")))
        pid = panel.process.processId()
        self.assertGreater(pid, 0)
        self.close_window()
        self.assertEqual(panel.process.state(), QProcess.ProcessState.NotRunning)
        self.assertEqual(panel.process.exitCode(), 0)

    def test_selector_change_stop_and_multiple_table(self):
        self.start("healthy")
        window, panel = self.window, self.window.simulator
        window.read_codes()
        self.idle()
        self.assertIn(EMPTY_CODES, window.codes_status.text())
        panel.stop_button.click()
        self.until(lambda: not panel.owned)
        self.idle()
        self.assertFalse(window.state["readings"])
        self.start("multiple_dtcs")
        window.read_codes()
        self.idle()
        self.assertEqual(window.codes_table.rowCount(), 3)
        self.assertEqual(window.codes_table.item(2, 2).text(), "Pendente")

    def test_loss_gui_stale_and_no_data_gui(self):
        self.start("connection_loss", loss=4)
        window, panel = self.window, self.window.simulator
        window.poll()
        self.idle()
        window.poll()
        self.idle()
        self.assertEqual(window.state["adapter_status"], "Desligado")
        self.assertTrue(all(r["stale"] for r in window.snapshot()["readings"]))
        panel.stop_button.click()
        self.until(lambda: not panel.owned)
        self.idle()
        self.start("no_data")
        window.read_codes()
        self.idle()
        self.assertIn(UNAVAILABLE, window.codes_status.text())
        self.assertNotIn(EMPTY_CODES, window.codes_status.text())

    def test_busy_port_preserves_external_server_and_no_local_controls(self):
        with socket.socket() as external:
            external.bind(("127.0.0.1", 0))
            external.listen(1)
            panel = self.window.simulator
            panel.port.setValue(external.getsockname()[1])
            panel.start_button.click()
            self.until(lambda: not panel.owned)
            self.assertIn("externo preservado", panel.process_status.text())
            self.assertFalse(panel.cycle_button.isEnabled())
            self.assertFalse(panel.stop_button.isEnabled())
            with socket.create_connection(external.getsockname(), timeout=1):
                accepted, _address = external.accept()
                accepted.close()

    def test_missing_environment_and_close_during_start(self):
        panel = self.window.simulator
        with patch.dict(os.environ, {"ELM327_PYTHON": str(ROOT / "absent/python.exe")}):
            panel.start_button.click()
        self.assertIn("não encontrado", panel.process_status.text())
        self.assertFalse(panel.owned)
        panel.port.setValue(free_port())
        panel.start_button.click()
        self.close_window()
        self.assertFalse(panel.owned)

    def test_external_connection_is_not_managed_or_stopped(self):
        external = RunningSimulator("healthy")
        self.addCleanup(external.close)
        window, panel = self.window, self.window.simulator
        window.port.setValue(external.port)
        window.connect_button.click()
        self.idle()
        self.assertIn("Servidor externo", window.connection_status.text())
        self.assertFalse(panel.cycle_button.isEnabled())
        panel.port.setValue(external.port)
        panel.start_button.click()
        self.until(lambda: not panel.owned)
        self.assertEqual(window.state["adapter_status"], "Ligado")
        self.close_window()
        self.assertIsNone(external.process.poll())
        self.assertEqual(external.control("status")[0], 200)

    def test_forced_shutdown_only_owned_process_tree(self):
        self.start("healthy")
        panel = self.window.simulator
        control_port = panel.control_port
        with patch.object(panel, "request", return_value=False):
            self.close_window()
        self.assertFalse(panel.owned)
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", control_port), timeout=1)


if __name__ == "__main__":
    unittest.main()
