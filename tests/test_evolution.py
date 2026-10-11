from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from fake_adapter import FakeAdapter
from test_stateful_simulator import RunningSimulator, find_emulator_python
from scanner_outo.config import Settings
from scanner_outo.diagnostics.obd import PIDS, ObdFrame, ObdDecodeError, decode_pid, decode_monitor_status
from scanner_outo.diagnostics.timeseries import ReadingSeries
from scanner_outo.gemini import analysis_payload, analysis_fingerprint, GeminiService
from scanner_outo.models import Session, ConnectionConfig, AVAILABLE, COMPLETE, UNAVAILABLE
from scanner_outo.persistence import SessionStore
from scanner_outo.services import DiagnosticService
from scanner_outo.ui.main_window import MainWindow


class DecoderEvolutionTests(unittest.TestCase):
    def test_all_twelve_limits_lengths_and_zero(self):
        limits = {4: (0, 100), 5: (-40, 215), 6: (-100, 99.21875), 7: (-100, 99.21875),
                  11: (0, 255), 12: (0, 16383.75), 13: (0, 255), 14: (-64, 63.5),
                  15: (-40, 215), 16: (0, 655.35), 17: (0, 100), 66: (0, 65.535)}
        self.assertEqual(set(PIDS), set(limits))
        for pid, definition in PIDS.items():
            with self.subTest(pid=pid):
                prefix = bytes([0x41, pid])
                self.assertAlmostEqual(decode_pid(ObdFrame("7E8", prefix + bytes(definition.length)), pid), limits[pid][0])
                self.assertAlmostEqual(decode_pid(ObdFrame("7E8", prefix + b"\xff" * definition.length), pid), limits[pid][1])
                for length in (definition.length - 1, definition.length + 1):
                    with self.assertRaises(ObdDecodeError):
                        decode_pid(ObdFrame("7E8", prefix + bytes(length)), pid)
                with self.assertRaises(ObdDecodeError):
                    decode_pid(ObdFrame("7E8", bytes([0x42, pid]) + bytes(definition.length)), pid)
        self.assertEqual(decode_pid(ObdFrame("7E8", b"\x41\x06\x80"), 6), 0)

    def test_monitor_spark_compression_reserved_bits_and_lengths(self):
        spark = decode_monitor_status(ObdFrame("7E8", bytes.fromhex("410181174525")))
        self.assertTrue(spark["mil"])
        self.assertEqual(spark["confirmed_count"], 1)
        self.assertEqual(len(spark["monitors"]), 6)
        self.assertFalse(spark["monitors"][0]["complete"])
        diesel = decode_monitor_status(ObdFrame("7E9", bytes.fromhex("41010009FF40")))
        self.assertIn("compressão", diesel["engine_type"])
        self.assertEqual(len(diesel["monitors"]), 7)
        self.assertTrue(any(m["name"] == "Filtro de partículas" and not m["complete"] for m in diesel["monitors"]))
        self.assertEqual(decode_monitor_status(ObdFrame("7E8", bytes.fromhex("410100001010")))["monitors"], [])
        for length in (0, 3, 5):
            with self.assertRaises(ObdDecodeError):
                decode_monitor_status(ObdFrame("7E8", b"\x41\x01" + bytes(length)))

    def test_chained_maps_only_eligible_ecu_and_selected_supported_pids(self):
        adapter = FakeAdapter()
        self.addCleanup(adapter.close)
        adapter.responses.update({"0100": "7E8 06 41 00 00 10 00 01\r7E9 06 41 00 00 10 00 00\r>",
                                  "0120": "7E8 06 41 20 00 00 00 01\r>",
                                  "0140": "7E8 06 41 40 40 00 00 00\r>",
                                  "0142": "7E8 04 41 42 37 78\r>"})
        service = DiagnosticService()
        self.addCleanup(service.disconnect)
        connected = service.connect(ConnectionConfig(port=adapter.port))
        self.assertIn(66, connected["supported"]["7E8"])
        self.assertNotIn(66, connected["supported"]["7E9"])
        for command in ("0120", "0140"):
            index = adapter.commands.index(command)
            self.assertEqual(adapter.commands[index - 1], "ATSH7E0")
            self.assertEqual(adapter.commands[index + 1], "ATSH7DF")
        adapter.commands.clear()
        snapshot = service.poll([66, 5])
        self.assertEqual(adapter.commands, ["ATSH7E0", "0142", "ATSH7DF"])
        voltage = next(r for r in snapshot["readings"] if r["pid"] == "42" and r["ecu"] == "7E8")
        self.assertEqual(voltage["value"], 14.2)
        self.assertEqual(next(r for r in snapshot["readings"] if r["pid"] == "42" and r["ecu"] == "7E9")["value"], None)

    def test_map_failure_does_not_guess_high_pids(self):
        adapter = FakeAdapter()
        self.addCleanup(adapter.close)
        adapter.responses["0100"] = "7E8 06 41 00 00 10 00 01\r>"
        service = DiagnosticService()
        self.addCleanup(service.disconnect)
        state = service.connect(ConnectionConfig(port=adapter.port))
        self.assertIn("01/7E8/20", state["support_queries"])
        service.poll([66])
        self.assertNotIn("0140", adapter.commands)
        self.assertNotIn("0142", adapter.commands)

    def test_bad_ecu_payload_does_not_invalidate_other_ecu(self):
        adapter = FakeAdapter()
        self.addCleanup(adapter.close)
        adapter.responses["010C"] = "7E8 04 41 0C 0B B8\r7E9 03 41 0C 00\r>"
        service = DiagnosticService()
        self.addCleanup(service.disconnect)
        service.connect(ConnectionConfig(port=adapter.port))
        values = {r["ecu"]: r for r in service.poll([12])["readings"] if r["pid"] == "0C"}
        self.assertEqual(values["7E8"]["value"], 750)
        self.assertEqual(values["7E8"]["status"], AVAILABLE)
        self.assertIsNone(values["7E9"]["value"])
        self.assertEqual(values["7E9"]["status"], "Falha de consulta")

    def test_continuation_stops_independently_and_29bit_addressing(self):
        service = DiagnosticService()
        calls = []
        def query(command):
            calls.append(command)
            return {
                "0100": [ObdFrame("7E8", bytes.fromhex("410000000001")), ObdFrame("7E9", bytes.fromhex("410000000001"))],
                "0120": [ObdFrame("7E8", bytes.fromhex("412000000001")), ObdFrame("7E9", bytes.fromhex("412000000000"))],
                "0140": [ObdFrame("7E8", bytes.fromhex("414040000000"))],
            }[command]
        from unittest.mock import MagicMock
        service.client = MagicMock()
        service.client.send.return_value.response = "OK"
        service.query = query
        supported = service.discover_support()
        self.assertEqual(calls, ["0100", "0120", "0140"])
        self.assertIn(66, supported["7E8"])
        self.assertNotIn(66, supported["7E9"])
        service.query = lambda _: [ObdFrame("18DAF110", bytes.fromhex("41423778"))]
        service.targeted_query("0142", ["18DAF110"], ["18DAF110", "18DAF118"])
        self.assertEqual([c.args[0] for c in service.client.send.call_args_list][-2:], ["ATSH18DA10F1", "ATSH18DB33F1"])
        with self.assertRaises(ObdDecodeError):
            service.targeted_query("0142", ["10"], ["10", "11"])


class TemporalEvolutionTests(unittest.TestCase):
    def session(self, instant):
        session = Session(adapter_status="Ligado").to_dict()
        session["readings"] = [{"pid": "0D", "name": "Velocidade", "unit": "km/h", "ecu": "7E8", "value": 0,
                                "status": AVAILABLE, "stale": False, "detail": "", "timestamp": instant.isoformat(), "attempted_at": instant.isoformat()}]
        return session

    def test_series_gaps_bound_ecus_and_session_reset(self):
        now = datetime.now(timezone.utc)
        session = self.session(now)
        series = ReadingSeries(3)
        series.ingest(session)
        series.ingest(session)
        self.assertEqual(len(series.samples[("0D", "7E8")]), 1)
        session["readings"][0].update(status=UNAVAILABLE, attempted_at=(now + timedelta(seconds=1)).isoformat())
        series.ingest(session)
        self.assertIsNone(series.samples[("0D", "7E8")][-1][1])
        session["readings"][0].update(status=AVAILABLE, value=2, timestamp=(now + timedelta(seconds=2)).isoformat(), attempted_at=(now + timedelta(seconds=2)).isoformat())
        series.ingest(session)
        self.assertEqual(len(series.segments("0D")["7E8"]), 2)
        self.assertEqual(series.segments("0D")["7E8"][0][0][1], 0)
        series.interrupt()
        self.assertEqual(len(series.samples[("0D", "7E8")]), 3)
        other = copy.deepcopy(session["readings"][0])
        other.update(ecu="7E9", value=40)
        session["readings"].append(other)
        series.ingest(session)
        self.assertEqual(set(series.segments("0D")), {"7E8", "7E9"})
        for index in range(3, 8):
            session["readings"][0].update(timestamp=(now + timedelta(seconds=index)).isoformat(), attempted_at=(now + timedelta(seconds=index)).isoformat())
            series.ingest(session)
        self.assertEqual(len(series.samples[("0D", "7E8")]), 3)
        session["created_at"] = "another-session"
        session["readings"] = []
        series.ingest(session)
        self.assertFalse(series.samples)

    def test_snapshot_immutable_age_validity_warnings_and_cache(self):
        instant = datetime.now(timezone.utc)
        session = self.session(instant)
        first = analysis_payload(session, "ralenti", instant)
        second = analysis_payload(session, "ralenti", instant + timedelta(seconds=1))
        self.assertEqual(first["parametros"][0]["idade_segundos"], 0)
        self.assertEqual(second["parametros"][0]["idade_segundos"], 1)
        self.assertEqual(analysis_fingerprint(first), analysis_fingerprint(second))
        stale = analysis_payload(session, "ralenti", instant + timedelta(seconds=11))
        self.assertEqual(stale["parametros"][0]["validade"], "Desactualizado")
        self.assertNotEqual(analysis_fingerprint(first), analysis_fingerprint(stale))
        self.assertEqual(len(stale["avisos"]), 2)
        session["readings"][0]["value"] = 99
        self.assertEqual(first["parametros"][0]["value"], 0)
        with tempfile.TemporaryDirectory() as temp:
            settings = Settings(data_dir=Path(temp), api_key="ficticia", daily_limit=20, minimum_interval=0)
            calls, clock = [], [100]
            def generate(*args):
                calls.append(args)
                return {"text": json.dumps({k: [] for k in ("factos_medidos", "hipoteses", "evidencias", "informacao_em_falta", "proximos_testes")})}
            service = GeminiService(settings, SessionStore(Path(temp) / "db.sqlite3"), generate, lambda: clock[0])
            result = service.analyze(first, "simulado")
            cached = service.analyze(second, "simulado")
            self.assertTrue(cached["cache"])
            self.assertEqual(cached["captured_at"], first["capturado_em"])
            self.assertEqual(cached["analyzed_at"], result["analyzed_at"])
            self.assertFalse(service.analyze(stale, "simulado")["cache"])
            clock[0] = 401
            self.assertFalse(service.analyze(second, "simulado")["cache"])
            self.assertEqual(len(calls), 3)

    def test_legacy_snapshot_without_new_fields_is_preserved(self):
        session = self.session(datetime.now(timezone.utc))
        for key in ("monitor_status", "monitor_query", "support_queries"):
            session.pop(key)
        session["readings"][0].pop("attempted_at")
        original = copy.deepcopy(session)
        with tempfile.TemporaryDirectory() as temp:
            store = SessionStore(Path(temp) / "legacy.sqlite3")
            identifier = store.save(session)
            loaded = store.load(identifier)
            payload = analysis_payload(loaded, "teste antigo")
            self.assertEqual(payload["estado_consulta_mil"]["status"], "Não consultado")
            self.assertEqual(loaded, original)
            store.export(identifier, Path(temp) / "legacy.json")
            self.assertEqual(json.loads((Path(temp) / "legacy.json").read_text(encoding="utf-8")), original)


class RealTcpEvolutionTests(unittest.TestCase):
    def setUp(self):
        if find_emulator_python() is None:
            self.skipTest("ELM327-emulator não encontrado")
        self.simulator = RunningSimulator("rough_idle_p0301")
        self.addCleanup(self.simulator.close)
        self.service = DiagnosticService()
        self.addCleanup(self.service.disconnect)
        self.service.connect(ConnectionConfig(port=self.simulator.port, timeout=2))

    def test_twelve_actual_tcp_freeze_mil_and_clear_cycles(self):
        state = self.service.poll(PIDS)
        self.assertEqual(len(state["readings"]), 12)
        self.assertTrue(all(r["status"] == AVAILABLE and r["value"] is not None for r in state["readings"]))
        self.assertEqual(next(r["value"] for r in state["readings"] if r["pid"] == "42"), 14.2)
        freeze = self.service.read_freeze_frame()
        self.assertEqual(len(freeze["freeze_frame"]), 12)
        self.assertEqual(next(r["value"] for r in freeze["freeze_frame"] if r["pid"] == "42"), 14)
        status = self.service.read_codes()["monitor_status"]["7E8"]
        self.assertTrue(status["mil"])
        self.assertEqual(status["confirmed_count"], 1)
        self.assertEqual(status["monitors"], [{"name": "Falhas de combustão", "complete": True}])
        cleared = self.service.clear_codes()
        self.assertFalse(cleared["monitor_status"]["7E8"]["mil"])
        self.assertFalse(cleared["monitor_status"]["7E8"]["monitors"][0]["complete"])
        self.simulator.control("cycle")
        pending = self.service.read_codes()
        self.assertFalse(pending["monitor_status"]["7E8"]["mil"])
        self.assertEqual(pending["codes"][0]["status"], "Pendente")
        self.simulator.control("cycle")
        self.assertTrue(self.service.read_codes()["monitor_status"]["7E8"]["mil"])
        self.simulator.control("resolve")
        recovered = self.service.poll(PIDS)
        self.assertEqual(next(r["value"] for r in recovered["readings"] if r["pid"] == "0C"), 750)
        self.assertTrue(self.service.read_codes()["monitor_status"]["7E8"]["mil"])

    def test_gui_graph_status_and_explicit_mock_analysis(self):
        self.service.disconnect()
        app = QApplication.instance() or QApplication([])
        self.assertIsNotNone(app)
        with tempfile.TemporaryDirectory() as temp, patch("scanner_outo.gemini.official_generate", side_effect=AssertionError("Chamada real proibida")) as remote:
            window = MainWindow(Settings(data_dir=Path(temp), api_key="ficticia", minimum_interval=0))
            def idle():
                for _ in range(750):
                    QTest.qWait(20)
                    if not any(window.busy.values()):
                        QTest.qWait(100)
                        return
                self.fail("Worker não terminou: " + window.last_error)
            try:
                window.show()
                idle()
                window.port.setValue(self.simulator.port)
                window.connect_adapter()
                idle()
                self.assertEqual(window.state["adapter_status"], "Ligado", window.last_error)
                for action in window.pid_actions.values():
                    action.setChecked(True)
                ticks = []
                timer = QTimer(window)
                timer.timeout.connect(lambda: ticks.append(1))
                timer.start(10)
                window.tabs.setCurrentIndex(1)
                window.data_views.setCurrentIndex(1)
                window.poll()
                idle()
                window.read_codes()
                idle()
                self.assertEqual(window.monitor_table.item(0, 1).text(), "Acesa")
                self.assertEqual(window.codes_table.item(0, 0).text(), "P0301")
                self.assertEqual(len(window.series.samples), 12)
                self.assertTrue(window.reading_chart.chart.series())
                self.assertEqual(window.reading_chart.time_axis.titleText(), "Hora local")
                self.assertLess(window.reading_chart.time_axis.min(), window.reading_chart.time_axis.max())
                self.assertGreater(len(ticks), 3)
                calls = []
                def generate(_settings, _model, payload):
                    calls.append(payload)
                    self.assertTrue(all(r["validade"] == "Recente" for r in payload["parametros"]))
                    self.assertEqual(payload["origem"], "Emulador / simulação")
                    self.assertEqual(payload["sintomas"], "Motor treme ao ralenti")
                    return {"text": json.dumps({"factos_medidos": ["P0301 recebido por OBD"], "hipoteses": ["Ignição, alimentação ou compressão; não identifica uma peça"], "evidencias": [], "informacao_em_falta": [], "proximos_testes": ["Testar ignição e compressão"]})}
                window.gemini.generate = generate
                window.symptoms.setPlainText("Motor treme ao ralenti")
                window.analyze()
                idle()
                self.assertEqual(len(calls), 1)
                self.assertNotIn("Dados alterados", window.analysis_validity.text())
                window.symptoms.setPlainText("Sintoma alterado")
                self.assertIn("Dados alterados", window.analysis_validity.text())
                window.symptoms.setPlainText("Motor treme ao ralenti")
                points = copy.deepcopy(window.series.samples)
                window.stop_polling()
                self.assertEqual(window.series.samples, points)
                self.assertIn("Dados alterados", window.analysis_validity.text())
                self.assertEqual(len(calls), 1)
                artifact = Path(__file__).resolve().parents[1] / "artifacts"
                artifact.mkdir(exist_ok=True)
                for size in ((1120, 740), (860, 600)):
                    window.resize(*size)
                    for index in (1, 2, 3, 5):
                        window.tabs.setCurrentIndex(index)
                        if index == 1:
                            window.data_views.setCurrentIndex(1)
                        QTest.qWait(80)
                        self.assertTrue(window.grab().save(str(artifact / f"evolution-{size[0]}-tab{index}.png")))
                window.save_session()
                idle()
                self.assertEqual(len(window.store.list_sessions()), 1)
                window.disconnect_adapter()
                idle()
                self.assertTrue(window.ai_output.toPlainText())
                window.connect_adapter()
                idle()
                self.assertFalse(window.series.samples)
                self.assertIn("Dados alterados", window.analysis_validity.text())
                remote.assert_not_called()
            finally:
                window.close()
                idle()

    def test_healthy_and_multiple_twelve_tcp_values(self):
        self.service.disconnect()
        for scenario, trim in (("healthy", 1.5625), ("multiple_dtcs", 25)):
            with self.subTest(scenario=scenario):
                simulator = RunningSimulator(scenario)
                service = DiagnosticService()
                try:
                    service.connect(ConnectionConfig(port=simulator.port, timeout=2))
                    values = {r["pid"]: r for r in service.poll(PIDS)["readings"]}
                    self.assertEqual(len(values), 12)
                    self.assertTrue(all(r["status"] == AVAILABLE for r in values.values()))
                    self.assertEqual(values["06"]["value"], trim)
                    status = service.read_codes()["monitor_status"]["7E8"]
                    self.assertEqual(status["confirmed_count"], 0 if scenario == "healthy" else 2)
                    if scenario == "multiple_dtcs":
                        simulator.control("resolve")
                        values = {r["pid"]: r for r in service.poll(PIDS)["readings"]}
                        self.assertEqual(values["06"]["value"], 1.5625)
                        self.assertEqual(values["0C"]["value"], 750)
                finally:
                    service.disconnect()
                    simulator.close()
