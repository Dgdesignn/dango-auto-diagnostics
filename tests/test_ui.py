from __future__ import annotations

import json
import socket
import tempfile
import time
import unittest
from unittest.mock import patch
from pathlib import Path
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import QTimer, QThread
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from fake_adapter import FakeAdapter
from scanner_outo.config import Settings
from scanner_outo.ui.main_window import MainWindow


class GuiTests(unittest.TestCase):
    real_emulator = False
    app = None

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.adapter = None if self.real_emulator else FakeAdapter()
        if self.adapter:
            self.addCleanup(self.adapter.close)
        self.window = MainWindow(Settings(data_dir=Path(self.temp.name), api_key=""))
        self.window.port.setValue(35000 if self.real_emulator else self.adapter.port)
        self.window.show()
        self.wait_idle()
        self.addCleanup(self.close_window)

    def close_window(self):
        self.window.close()
        self.wait_idle()
        QTest.qWait(100)

    def wait_idle(self, timeout=15000):
        deadline = time.monotonic() + timeout / 1000
        while any(self.window.busy.values()) and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertFalse(any(self.window.busy.values()), "Workers nao terminaram dentro do prazo")
        QTest.qWait(30)

    def test_full_read_only_workflow(self):
        ticks = []
        timer = QTimer()
        timer.timeout.connect(lambda: ticks.append(1))
        timer.start(10)
        self.addCleanup(timer.stop)
        self.window.connect_button.click()
        self.wait_idle()
        self.assertEqual(self.window.state["adapter_status"], "Ligado", self.window.last_error)
        self.window.tabs.setCurrentIndex(1)
        self.window.read_button.click()
        self.wait_idle()
        valid = [r for r in self.window.state["readings"] if r["status"] == "Disponivel"]
        self.assertTrue(valid, self.window.state)
        self.assertTrue(all(r["value"] is not None for r in valid))
        self.assertGreater(len(ticks), 3)
        self.assertEqual(QThread.currentThread(), self.window.thread())
        self.window.start_button.click()
        self.wait_idle()
        self.assertTrue(self.window.poll_timer.isActive())
        self.window.stop_button.click()
        self.assertFalse(self.window.poll_timer.isActive())
        self.window.read_codes()
        self.wait_idle()
        self.assertTrue(self.window.state["code_queries"])
        self.window.read_freeze()
        self.wait_idle()
        self.assertNotEqual(self.window.state["freeze_status"], "Nao consultado")
        self.window.symptoms.setPlainText("Teste de funcionamento da interface")
        self.window.analyze()
        self.wait_idle()
        self.assertIn("Chave Gemini nao configurada", self.window.ai_status.text())
        self.window.save_session()
        self.wait_idle()
        self.window.refresh_history()
        self.wait_idle()
        self.assertEqual(len(self.window.history_rows), 1)
        self.window.history_table.selectRow(0)
        self.window.open_history()
        self.wait_idle()
        dialogs = [dialog for dialog in self.window.findChildren(QDialog) if dialog.isVisible()]
        self.assertTrue(dialogs)
        for dialog in dialogs:
            self.assertTrue(dialog.grab().save(str(Path(self.temp.name) / "historico.png")))
            dialog.close()
        session_id = self.window.selected_session_id()
        export = Path(self.temp.name) / "export.json"
        self.window.store.export(session_id, export)
        self.assertEqual(json.loads(export.read_text(encoding="utf-8"))["symptoms"], "Teste de funcionamento da interface")
        self.window.tabs.setCurrentIndex(1)
        artifact = Path(__file__).resolve().parents[1] / "artifacts"
        artifact.mkdir(exist_ok=True)
        prefix = "real" if self.real_emulator else "fake"
        self.assertTrue(self.window.grab().save(str(artifact / f"gui-{prefix}-1120.png")))
        for index, name in ((0, "ligacao"), (2, "avarias"), (3, "ia"), (4, "historico")):
            self.window.tabs.setCurrentIndex(index)
            QTest.qWait(30)
            self.assertTrue(self.window.grab().save(str(artifact / f"gui-{prefix}-{name}.png")))
        self.window.tabs.setCurrentIndex(1)
        self.window.resize(860, 600)
        QTest.qWait(50)
        self.assertEqual(self.window.width(), 860)
        self.assertTrue(self.window.grab().save(str(artifact / f"gui-{prefix}-860.png")))
        for index, name in ((0, "ligacao"), (2, "avarias"), (3, "ia"), (4, "historico")):
            self.window.tabs.setCurrentIndex(index)
            QTest.qWait(30)
            self.assertTrue(self.window.grab().save(str(artifact / f"gui-{prefix}-{name}-860.png")))
        print("GUI leituras:", [(r["ecu"], r["name"], r["value"], r["unit"]) for r in valid])
        print("GUI codigos:", self.window.state["code_queries"])
        print("GUI freeze frame:", self.window.state["freeze_status"])
        self.window.disconnect_button.click()
        self.wait_idle()
        self.assertEqual(self.window.state["adapter_status"], "Desligado")
        self.window.connect_button.click()
        self.wait_idle()
        self.assertEqual(self.window.state["adapter_status"], "Ligado")
        if self.adapter:
            self.assertNotIn("04", self.adapter.commands)

    def test_unavailable_emulator_and_old_reading(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.window.port.setValue(port)
        self.window.connect_button.click()
        self.wait_idle()
        self.assertEqual(self.window.state["adapter_status"], "Desligado")
        self.assertIn("Nao foi possivel ligar", self.window.last_error)
        self.assertTrue(self.window.connect_button.isEnabled())

    def test_reading_age_and_gui_thread_callbacks(self):
        threads = []
        self.window.launch("other", lambda: 42, lambda _: threads.append(QThread.currentThread()), "Teste worker")
        self.wait_idle()
        self.assertEqual(threads, [self.window.thread()])
        self.window.state["readings"] = [{"pid": "0C", "name": "RPM", "unit": "rpm", "ecu": "7E8", "value": 1304, "status": "Disponivel", "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), "detail": ""}]
        self.window.render_readings()
        self.assertEqual(self.window.data_table.item(0, 5).text(), "Desactualizado")
        self.assertEqual(self.window.data_table.item(0, 2).text(), "1304")

    def test_simulated_gemini_result_and_preservation(self):
        self.window.settings.api_key = "ficticia-teste-ui"
        result = {key: ["Texto de teste"] for key in ("factos_medidos", "hipoteses", "evidencias", "informacao_em_falta", "proximos_testes")}
        self.window.gemini.generate = lambda *_: {"text": json.dumps(result), "tokens": {"total": 25}}
        self.window.analyze()
        self.wait_idle()
        self.assertIn("Texto de teste", self.window.ai_output.toPlainText())
        self.assertIn("25", self.window.ai_status.text())
        snapshot = self.window.service.session.to_dict()
        self.window.apply_state(snapshot)
        self.assertEqual(self.window.state["analysis"]["result"], result)

    def test_clear_cancel_keeps_snapshot_without_sending_command(self):
        if self.real_emulator:
            self.skipTest("Confirmacao de limpeza testada apenas com substituto, sem enviar 04")
        self.window.connect_button.click()
        self.wait_idle()
        with patch("scanner_outo.ui.main_window.QMessageBox.question", return_value=QMessageBox.StandardButton.No) as question:
            self.window.prepare_clear()
            self.wait_idle()
            QTest.qWait(100)
            self.assertEqual(question.call_count, 1)
        self.assertEqual(self.window.store.list_sessions()[0]["label"], "Fotografia antes da limpeza")
        self.assertNotIn("04", self.adapter.commands)

    def test_close_during_worker(self):
        if self.real_emulator:
            self.skipTest("Cancelamento controlado usa servidor substituto")
        self.window.connect_button.click()
        self.wait_idle()
        self.adapter.delay = 0.2
        self.window.poll()
        self.window.close()
        self.wait_idle()
        QTest.qWait(100)
        self.assertFalse(self.window.isVisible())
