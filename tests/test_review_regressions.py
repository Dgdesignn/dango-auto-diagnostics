from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLabel

from fake_adapter import FakeAdapter
from scanner_outo.communication.base import TransportError
from scanner_outo.config import Settings
from scanner_outo.gemini import analysis_payload, saved_analysis_correspondence
from scanner_outo.models import (
    Session, Reading, ConnectionConfig, NOT_QUERIED, COMPLETE, PARTIAL, NO_USABLE_DATA,
    UNAVAILABLE, QUERY_FAILED, AVAILABLE, SUPPORT_UNKNOWN, UNSUPPORTED,
)
from scanner_outo.persistence import SessionStore
from scanner_outo.services import DiagnosticService
from scanner_outo.ui.main_window import MainWindow


RESULT = {key: ["Resultado simulado"] for key in (
    "factos_medidos", "hipoteses", "evidencias", "informacao_em_falta", "proximos_testes",
)}


def saved_photo():
    instant = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    session = Session(adapter_status="Ligado", symptoms="Motor irregular", captured_at=instant.isoformat()).to_dict()
    session["freshness_seconds"] = 10
    session["readings"] = [Reading("0C", "RPM", "rpm", "7E8", 740, AVAILABLE,
                                    (instant - timedelta(seconds=1)).isoformat()).__dict__.copy()]
    payload = analysis_payload(session, session["symptoms"], captured_at=instant)
    session["analysis_input"] = payload
    session["analysis"] = {"result": copy.deepcopy(RESULT), "model": "simulado", "tokens": {}, "cache": False,
                           "captured_at": payload["capturado_em"], "analyzed_at": (instant + timedelta(seconds=2)).isoformat()}
    return session


class MapReviewTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FakeAdapter()
        self.addCleanup(self.adapter.close)
        self.service = DiagnosticService()
        self.addCleanup(self.service.disconnect)

    def connect(self):
        return self.service.connect(ConnectionConfig(port=self.adapter.port))

    @staticmethod
    def reading(state, pid="42", ecu="7E8", field="readings"):
        return next(r for r in state[field] if r["pid"] == pid and r["ecu"] == ecu)

    def test_failed_0120_leaves_42_unknown_and_earlier_rpm_confirmed(self):
        self.adapter.responses["0100"] = "7E8 06 41 00 00 10 00 01\r>"
        for response in ("NO DATA\r>", "7E8 05 41 20 00 00 00\r>"):
            with self.subTest(response=response):
                self.adapter.responses["0120"] = response
                state = self.connect()
                voltage = self.reading(state)
                self.assertEqual(voltage["status"], SUPPORT_UNKNOWN)
                self.assertIn("0120", voltage["detail"])
                self.assertIsNone(voltage["value"])
                self.assertEqual(self.reading(state, "0C")["status"], NOT_QUERIED)
                self.adapter.commands.clear()
                state = self.service.poll([0x42, 0x0C])
                self.assertIn("010C", self.adapter.commands)
                self.assertNotIn("0142", self.adapter.commands)
                self.assertNotIn("0140", self.adapter.commands)
                self.assertEqual(self.reading(state)["status"], SUPPORT_UNKNOWN)

    def test_valid_0140_confirms_absent_voltage(self):
        self.adapter.responses.update({"0100": "7E8 06 41 00 00 10 00 01\r>",
                                       "0120": "7E8 06 41 20 00 00 00 01\r>",
                                       "0140": "7E8 06 41 40 00 00 00 00\r>"})
        voltage = self.reading(self.connect())
        self.assertEqual(voltage["status"], UNSUPPORTED)
        self.assertIn("0140", voltage["detail"])
        self.service.poll([0x42])
        self.assertNotIn("0142", self.adapter.commands)

    def test_absent_continuation_confirms_later_pids_unsupported(self):
        for base in (0, 0x20):
            with self.subTest(base=base):
                self.adapter.responses["0100"] = "7E8 06 41 00 00 10 00 " + ("00\r>" if base == 0 else "01\r>")
                self.adapter.responses["0120"] = "7E8 06 41 20 00 00 00 00\r>"
                self.adapter.commands.clear()
                voltage = self.reading(self.connect())
                self.assertEqual(voltage["status"], UNSUPPORTED)
                self.assertIn("sem continuação", voltage["detail"])
                self.assertNotIn("0140", self.adapter.commands)
                if base == 0:
                    self.assertNotIn("0120", self.adapter.commands)

    def test_different_ecu_maps_do_not_share_unknown_support(self):
        self.adapter.responses.update({"0100": "7E8 06 41 00 00 10 00 01\r7E9 06 41 00 00 10 00 01\r>",
                                       "0120": "7E8 05 41 20 00 00 00\r7E9 06 41 20 00 00 00 01\r>",
                                       "0140": "7E9 06 41 40 40 00 00 00\r>",
                                       "0142": "7E9 04 41 42 37 78\r>"})
        state = self.connect()
        self.assertEqual(self.reading(state, ecu="7E8")["status"], SUPPORT_UNKNOWN)
        self.assertEqual(self.reading(state, ecu="7E9")["status"], NOT_QUERIED)
        self.adapter.commands.clear()
        state = self.service.poll([0x42])
        self.assertEqual(self.adapter.commands, ["ATSH7E1", "0142", "ATSH7DF"])
        self.assertEqual(self.reading(state, ecu="7E9")["value"], 14.2)
        self.assertIsNone(self.reading(state)["value"])

    def test_mode02_failure_is_independent_and_not_queried(self):
        self.connect()
        self.adapter.responses.update({"020000": "7E8 07 42 00 00 40 10 00 01\r>",
                                       "022000": "NO DATA\r>"})
        state = self.service.read_freeze_frame()
        voltage = self.reading(state, field="freeze_frame")
        self.assertEqual(voltage["status"], SUPPORT_UNKNOWN)
        self.assertIn("022000", voltage["detail"])
        self.assertNotIn("024200", self.adapter.commands)
        self.assertEqual(state["freeze_status"], PARTIAL)
        self.assertEqual(self.reading(state, "0C", field="freeze_frame")["status"], AVAILABLE)
        self.assertEqual(self.reading(state)["status"], UNSUPPORTED)
        self.assertIn("01/7E8/00", state["support_queries"])
        self.assertIn("02/7E8/20", state["support_queries"])


class FreezeReviewTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FakeAdapter()
        self.addCleanup(self.adapter.close)
        self.service = DiagnosticService()
        self.addCleanup(self.service.disconnect)
        self.service.connect(ConnectionConfig(port=self.adapter.port))

    def test_empty_valid_map_is_not_complete_or_no_freeze_proof(self):
        self.adapter.responses["020000"] = "7E8 07 42 00 00 00 00 00 00\r>"
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], NO_USABLE_DATA)
        self.assertFalse(state["freeze_frame"])
        self.assertIn("não confirma ausência", state["freeze_detail"])
        self.assertNotIn("020200", self.adapter.commands)

    def test_only_associated_code_is_partial(self):
        self.adapter.responses["020000"] = "7E8 07 42 00 00 40 00 00 00\r>"
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], PARTIAL)
        self.assertEqual(state["freeze_codes"], {"7E8": ["P0300"]})
        self.assertFalse(state["freeze_frame"])
        self.assertIn("Não foram obtidas leituras", state["freeze_detail"])

    def test_valid_unrecognized_pid_and_code_no_data(self):
        self.adapter.responses.update({"020000": "7E8 07 42 00 00 40 00 40 00\r>", "020200": "NO DATA\r>"})
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], NO_USABLE_DATA)
        self.assertIn("Sem dados", state["freeze_detail"])
        self.assertIn("parâmetros reconhecidos", state["freeze_detail"])

    def test_invalid_code_with_valid_readings_is_partial(self):
        self.adapter.responses["020200"] = "7E8 04 42 02 00 03\r>"
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], PARTIAL)
        self.assertEqual(len([r for r in state["freeze_frame"] if r["status"] == AVAILABLE]), 3)
        self.assertIn("Código de freeze frame incompleto", state["freeze_detail"])

    def test_valid_complete_freeze(self):
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], COMPLETE)
        self.assertEqual(state["freeze_ecus"]["7E8"]["status"], COMPLETE)
        self.assertEqual(len(state["freeze_frame"]), 3)

    def test_invalid_without_usable_data_is_failure(self):
        self.adapter.responses.update({"020000": "7E8 07 42 00 00 40 00 00 00\r>",
                                       "020200": "7E8 04 42 02 00 03\r>"})
        self.assertEqual(self.service.read_freeze_frame()["freeze_status"], QUERY_FAILED)

    def test_no_data_initial_map_is_unavailable(self):
        self.adapter.responses["020000"] = "NO DATA\r>"
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], UNAVAILABLE)
        self.assertFalse(state["freeze_codes"])
        self.assertFalse(state["freeze_frame"])

    def test_good_ecu_data_survives_bad_ecu_and_propagates(self):
        self.adapter.responses.update({"020000": "7E8 07 42 00 00 40 10 00 00\r7E9 07 42 00 00 40 10 00 00\r>",
                                       "020200": "7E8 05 42 02 00 03 01\r7E9 04 42 02 00 03\r>",
                                       "020C00": "7E8 05 42 0C 00 0B 18\r7E9 04 42 0C 00 03\r>"})
        state = self.service.read_freeze_frame()
        self.assertEqual(state["freeze_status"], PARTIAL)
        self.assertEqual(state["freeze_codes"], {"7E8": ["P0301"]})
        self.assertEqual(state["freeze_ecus"]["7E8"]["status"], COMPLETE)
        self.assertEqual(state["freeze_ecus"]["7E9"]["status"], QUERY_FAILED)
        self.assertEqual(state["freeze_frame"][0]["value"], 710)
        self.assertIsNone(state["freeze_frame"][1]["value"])
        payload = analysis_payload(state, "teste")
        self.assertEqual(payload["estado_freeze_frame"], PARTIAL)
        self.assertEqual(payload["detalhe_freeze_frame"], state["freeze_detail"])
        self.assertEqual(payload["estado_freeze_por_ecu"], state["freeze_ecus"])
        with tempfile.TemporaryDirectory() as temp:
            store = SessionStore(Path(temp) / "test.sqlite3")
            identifier = store.save(state)
            store.export(identifier, Path(temp) / "export.json")
            self.assertEqual(store.load(identifier), state)
            self.assertEqual(json.loads((Path(temp) / "export.json").read_text(encoding="utf-8")), state)

    def test_transport_failure_keeps_data_and_partial_status(self):
        original = self.service.targeted_query
        def query(command, *args):
            if command == "020500":
                raise TransportError("Falha controlada")
            return original(command, *args)
        with patch.object(self.service, "targeted_query", side_effect=query):
            with self.assertRaises(TransportError):
                self.service.read_freeze_frame()
        state = self.service.session.to_dict()
        self.assertEqual(state["freeze_status"], PARTIAL)
        self.assertEqual(state["freeze_frame"][0]["value"], 1726)
        self.assertIn("interrompida", state["freeze_detail"])


class HistoryReviewTests(unittest.TestCase):
    def test_corresponding_photo_uses_capture_not_opening_clock(self):
        photo = saved_photo()
        original = copy.deepcopy(photo)
        self.assertEqual(saved_analysis_correspondence(photo), "Análise corresponde à fotografia guardada")
        self.assertEqual(photo, original)

    def test_changed_photo_values_symptoms_codes_connection_or_validity(self):
        for field in ("value", "symptoms", "codes", "adapter_status", "stale"):
            photo = saved_photo()
            with self.subTest(field=field):
                if field == "value":
                    photo["readings"][0]["value"] = 820
                elif field == "stale":
                    photo["readings"][0]["stale"] = True
                elif field == "symptoms":
                    photo["symptoms"] = "Sintoma diferente"
                elif field == "codes":
                    photo["codes"] = [{"code": "P0301", "status": "Confirmado", "ecu": "7E8"}]
                else:
                    photo[field] = "Desligado"
                self.assertEqual(saved_analysis_correspondence(photo), "Dados da sessão diferem dos usados nesta análise")

    def test_legacy_missing_capture_or_metadata_and_no_analysis(self):
        for field in ("captured_at", "analysis_input"):
            photo = saved_photo()
            photo.pop(field)
            self.assertEqual(saved_analysis_correspondence(photo), "Correspondência não verificável")
        photo = saved_photo()
        photo["analysis_input"] = {"parametros": photo["readings"]}
        self.assertEqual(saved_analysis_correspondence(photo), "Correspondência não verificável")
        photo["analysis"] = None
        self.assertEqual(saved_analysis_correspondence(photo), "Sem análise guardada")


class ReviewGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.adapter = FakeAdapter()
        self.addCleanup(self.adapter.close)
        self.window = MainWindow(Settings(data_dir=Path(self.temp.name), api_key="ficticia", minimum_interval=0))
        self.window.show()
        self.addCleanup(self.close_window)
        self.idle()
        self.window.port.setValue(self.adapter.port)

    def until(self, predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            QTest.qWait(20)
            if predicate():
                return
        self.fail("Timeout GUI: " + self.window.last_error)

    def idle(self, diag_only=False):
        self.until(lambda: not self.window.busy["diag"] if diag_only else not any(self.window.busy.values()))
        QTest.qWait(80)

    def close_window(self):
        for dialog in self.window.findChildren(QDialog):
            dialog.close()
        self.window.close()
        self.idle()

    def delayed_response(self, cached=False):
        window = self.window
        window.connect_adapter()
        self.idle()
        old_token = window.state["created_at"]
        window.symptoms.setPlainText("Sintomas da sessão anterior")
        calls = []
        def generate(*_args):
            calls.append(1)
            return {"text": json.dumps(RESULT), "tokens": {"total": 10}}
        window.gemini.generate = generate
        if cached:
            window.gemini.analyze(analysis_payload(window.snapshot(), window.symptoms.toPlainText()), window.model.text())
        original = window.gemini.analyze
        started, release = threading.Event(), threading.Event()
        def delayed(payload, model):
            started.set()
            if not release.wait(60):
                raise RuntimeError("Timeout do cliente simulado")
            return original(payload, model)
        window.gemini.analyze = delayed
        try:
            with patch("scanner_outo.gemini.official_generate", side_effect=AssertionError("Gemini real proibido")) as remote:
                window.analyze()
                self.until(started.is_set)
                window.disconnect_adapter()
                self.idle(diag_only=True)
                window.connect_adapter()
                self.idle(diag_only=True)
                self.assertNotEqual(window.state["created_at"], old_token)
                self.assertTrue(window.busy["other"])
                release.set()
                self.idle()
                self.assertIn("sessão anterior", window.ai_status.text())
                self.assertNotIn("Análise concluída", window.ai_status.text())
                self.assertIn("Captura:", window.ai_status.text())
                self.assertIn("Resposta original:", window.ai_status.text())
                self.assertEqual(window.last_analysis["cache"], cached)
                if cached:
                    self.assertIn("Cache local", window.ai_status.text())
                self.assertTrue(window.ai_output.toPlainText())
                self.assertIsNone(window.state["analysis"])
                self.assertIsNone(window.state["analysis_input"])
                window.save_session()
                self.idle()
                identifier = window.store.list_sessions()[0]["id"]
                saved = window.store.load(identifier)
                self.assertIsNone(saved["analysis"])
                self.assertIsNone(saved["analysis_input"])
                self.assertTrue(saved["captured_at"])
                self.assertEqual(len(calls), 1)
                remote.assert_not_called()
        finally:
            release.set()
            self.idle()

    def test_response_from_previous_connection_stays_identified_and_unsaved(self):
        self.delayed_response()

    def test_cached_response_from_previous_connection_keeps_warning(self):
        self.delayed_response(cached=True)

    def test_history_shows_match_difference_legacy_and_no_analysis(self):
        window = self.window
        variants = []
        photo = saved_photo()
        variants.append((photo, "Análise corresponde à fotografia guardada"))
        changed = copy.deepcopy(photo)
        changed["symptoms"] = "Outro sintoma"
        variants.append((changed, "Dados da sessão diferem dos usados nesta análise"))
        old = copy.deepcopy(photo)
        old.pop("captured_at")
        variants.append((old, "Correspondência não verificável"))
        empty = copy.deepcopy(photo)
        empty["analysis"] = None
        empty["analysis_input"] = None
        variants.append((empty, "Sem análise guardada"))
        for photo, expected in variants:
            with self.subTest(expected=expected):
                identifier = window.store.save(photo)
                window.refresh_history()
                self.idle()
                index = next(i for i, row in enumerate(window.history_rows) if row["id"] == identifier)
                window.history_table.selectRow(index)
                window.open_history()
                self.idle()
                dialog = next(d for d in window.findChildren(QDialog) if d.isVisible())
                label = dialog.findChild(QLabel, "history_analysis_correspondence")
                self.assertEqual(label.text(), expected)
                self.assertEqual(window.store.load(identifier), photo)
                artifact = Path(__file__).resolve().parents[1] / "artifacts"
                artifact.mkdir(exist_ok=True)
                self.assertTrue(dialog.grab().save(str(artifact / f"review-history-{identifier}.png")))
                dialog.close()
