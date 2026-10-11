from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from fake_adapter import FakeAdapter
from scanner_outo.config import Settings
from scanner_outo.diagnostics.obd import PIDS
from scanner_outo.ui.main_window import MainWindow
from scanner_outo.ui.shell import NAVIGATION
from scanner_outo.ui.design import ASSETS, icon

ROOT = Path(__file__).resolve().parents[1]
RESULT = {"factos_medidos": ["Dados de simulação: P0301 confirmado e motor quente."],
          "hipoteses": ["Ignição, alimentação ou compressão; o DTC não identifica uma peça."],
          "evidencias": ["Origem emulador; ralenti irregular informado."],
          "informacao_em_falta": ["Inspecção e medições num veículo real."],
          "proximos_testes": ["Confirmar as hipóteses por medições antes de substituir componentes."]}


class StitchUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.window = MainWindow(Settings(data_dir=Path(self.temp.name), api_key="ficticia", minimum_interval=0))
        self.window.show()
        self.addCleanup(self.close_window)
        self.idle()

    def until(self, predicate, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            QTest.qWait(20)
            if predicate():
                return
        self.fail("Timeout Qt: " + self.window.last_error + " | " + self.window.simulator.process_status.text())

    def idle(self):
        self.until(lambda: not any(self.window.busy.values()) and not self.window.simulator.busy)
        QTest.qWait(80)

    def close_window(self):
        for dialog in self.window.findChildren(QDialog):
            dialog.close()
        self.window.close()
        self.until(lambda: not self.window.isVisible() and not self.window.simulator.owned)

    def go(self, index):
        QTest.mouseClick(self.window.shell.navigation[index], Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.tabs.currentIndex(), index)

    def test_navigation_is_read_only_and_assets_are_offline(self):
        window = self.window
        calls = []
        window.gemini.generate = lambda *_: calls.append(1)
        before = window.state.copy()
        timers = window.poll_timer, window.age_timer
        for _ in range(3):
            for index, title, symbol in NAVIGATION:
                self.go(index)
                self.assertEqual(window.shell.title.text(), title)
                self.assertFalse(icon(symbol).isNull())
        self.assertEqual(before, window.state)
        self.assertEqual(timers, (window.poll_timer, window.age_timer))
        self.assertFalse(window.poll_timer.isActive())
        self.assertEqual(calls, [])
        self.go(5)
        self.assertTrue(window.shell.navigation[5].isChecked())
        self.go(0)
        window.transport_choices[0].click()
        window.transport_choices[0].click()
        self.assertTrue(window.transport_choices[0].isChecked())
        self.assertIn("Inter", QFontDatabase.families())
        self.assertIn("JetBrains Mono", QFontDatabase.families())
        self.assertTrue((ASSETS / "fonts/Inter-OFL.txt").is_file())
        self.assertTrue((ASSETS / "icons/LICENSE.txt").is_file())
        self.assertEqual(len(window.pid_checks), 12)
        window.set_selected_pids(PIDS)
        self.assertTrue(all(c.isChecked() for c in window.pid_checks.values()))
        window.pid_checks[0x42].setChecked(False)
        self.assertNotIn(0x42, window.selected_pids())

    def test_manual_sidebar_in_compact_application(self):
        window = self.window
        window.resize(860, 600)
        QTest.qWait(100)
        self.assertEqual(window.shell.sidebar.width(), 72)
        window.shell.sidebar_toggle.click()
        QTest.qWait(300)
        self.assertEqual(window.shell.sidebar.width(), 260)
        folder = ROOT / "artifacts" / "stitch"
        folder.mkdir(parents=True, exist_ok=True)
        for index, _, _ in NAVIGATION:
            self.go(index)
            QTest.qWait(100)
            scroll = window.tabs.currentWidget()
            self.assertLessEqual(scroll.widget().minimumSizeHint().width(), scroll.viewport().width(), index)
        self.go(6)
        window.grab().save(str(folder / "sidebar-expanded-compact.png"))
        window.shell.sidebar_toggle.click()
        QTest.qWait(300)
        self.assertEqual(window.shell.sidebar.width(), 72)
        window.grab().save(str(folder / "sidebar-collapsed-compact.png"))

    def test_full_workflow_through_sidebar_and_visual_captures(self):
        window = self.window
        self.go(5)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        window.simulator.port.setValue(port)
        window.simulator.start_button.click()
        self.until(lambda: window.simulator.ready)
        self.idle()
        self.go(0)
        window.port.setValue(port)
        window.connect_button.click()
        self.idle()
        self.assertEqual(window.state["adapter_status"], "Ligado")
        self.go(1)
        window.set_selected_pids(PIDS)
        window.read_button.click()
        self.idle()
        for _ in range(2):
            window.read_button.click()
            self.idle()
        self.assertEqual(len([r for r in window.state["readings"] if r["value"] is not None]), 12)
        self.go(2)
        window.codes_button.click()
        self.idle()
        window.freeze_button.click()
        self.idle()
        self.assertEqual(window.state["codes"][0]["code"], "P0301")
        self.assertEqual(len(window.state["freeze_frame"]), 12)
        self.assertTrue(window.state["monitor_status"]["7E8"]["mil"])
        window.codes_table.selectRow(0)
        self.assertIn("P0301", window.dtc_detail.text())
        self.go(3)
        window.symptoms.setPlainText("Motor treme ao ralenti")
        calls = []
        def generate(_settings, _model, payload):
            calls.append(payload)
            return {"text": json.dumps(RESULT), "tokens": {"total": 10}}
        window.gemini.generate = generate
        with patch("scanner_outo.gemini.official_generate", side_effect=AssertionError("Sem chamadas reais")):
            window.analyze_button.click()
            self.idle()
            window.analyze_button.click()
            self.idle()
        self.assertEqual(len(calls), 1)
        self.assertTrue(window.last_analysis["cache"])
        self.assertEqual(calls[0]["origem"], "Emulador / simulação")
        self.assertTrue(all(s.text() != "Sem análise disponível" for s in window.ai_sections.values()))
        window.symptoms.setPlainText("Outro sintoma")
        self.assertIn("Dados alterados", window.analysis_validity.text())
        window.symptoms.setPlainText("Motor treme ao ralenti")
        self.go(4)
        window.save_button.click()
        self.idle()
        self.until(lambda: len(window.history_rows) == 1)
        window.history_table.selectRow(0)
        window.open_button.click()
        self.idle()
        for dialog in window.findChildren(QDialog):
            dialog.close()
        exported = Path(self.temp.name) / "session.json"
        with patch.object(QFileDialog, "getSaveFileName", return_value=(str(exported), "JSON")):
            window.export_button.click()
            self.idle()
        self.assertEqual(json.loads(exported.read_text(encoding="utf-8"))["codes"][0]["code"], "P0301")
        self.captures()
        self.go(2)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.clear_button.click()
            self.until(lambda: "releitura confirmadas" in window.state["clear_status"], timeout=40)
            self.idle()
        self.assertFalse(window.state["codes"])
        self.go(5)
        for _ in range(2):
            window.simulator.cycle_button.click()
            self.idle()
        self.go(2)
        window.codes_button.click()
        self.idle()
        self.assertEqual(window.state["codes"][0]["code"], "P0301")
        self.go(5)
        window.simulator.resolve_button.click()
        self.idle()
        self.go(2)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.clear_button.click()
            self.until(lambda: "releitura confirmadas" in window.state["clear_status"], timeout=40)
            self.idle()
        self.go(5)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            window.simulator.reset_button.click()
            self.until(lambda: window.state["adapter_status"] == "Desligado" and not window.simulator.transition)
            self.idle()
        self.assertFalse(window.state["codes"])

    def captures(self):
        window = self.window
        target = ROOT / "artifacts/stitch"
        target.mkdir(parents=True, exist_ok=True)
        scale = os.environ.get("QT_SCALE_FACTOR", "native")
        for width, height in ((1440, 900), (1120, 740), (860, 600)):
            window.resize(width, height)
            QTest.qWait(60)
            if QApplication.platformName() == "offscreen":
                self.assertEqual(window.size().width(), width)
                self.assertEqual(window.size().height(), height)
            self.assertEqual(window.shell.sidebar.width(), 72 if width == 860 else 260)
            for index, _title, _symbol in NAVIGATION:
                self.go(index)
                QTest.qWait(60)
                scroll = window.tabs.currentWidget()
                scroll.verticalScrollBar().setValue(0)
                path = target / f"{width}x{height}-scale{scale}-page{index}.png"
                self.assertTrue(window.grab().save(str(path)))
                if index == 1:
                    window.data_views.setCurrentIndex(1)
                    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                    QTest.qWait(60)
                    self.assertTrue(window.grab().save(str(target / f"{width}x{height}-scale{scale}-chart.png")))
                    window.data_views.setCurrentIndex(0)
                if index == 3:
                    for field in (window.model, window.daily, window.ai_interval):
                        self.assertFalse(window.symptoms.geometry().intersects(field.geometry()), "Formulário IA sobreposto")
                    self.assertGreaterEqual(window.model.parentWidget().height(), window.model.parentWidget().minimumSizeHint().height())
                if scroll.verticalScrollBar().maximum():
                    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
                    QTest.qWait(30)
                    self.assertTrue(window.grab().save(str(target / f"{width}x{height}-scale{scale}-bottom-page{index}.png")))

    def test_connection_loss_marks_overview_and_header_stale(self):
        adapter = FakeAdapter()
        self.addCleanup(adapter.close)
        window = self.window
        self.go(0)
        window.port.setValue(adapter.port)
        window.connect_button.click()
        self.idle()
        self.go(1)
        window.read_button.click()
        self.idle()
        adapter.close()
        window.read_button.click()
        self.idle()
        self.go(6)
        self.assertEqual(window.state["adapter_status"], "Desligado")
        self.assertIn("desactualizado", window.overview.cards["0C"].detail.text().lower())
        self.assertIn("Desligado", window.shell.badges["scanner"].text())
