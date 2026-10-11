import unittest

from fake_adapter import FakeAdapter
from scanner_outo.models import ConnectionConfig
from scanner_outo.services import DiagnosticService
from scanner_outo.communication.base import TransportError


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FakeAdapter()
        self.addCleanup(self.adapter.close)
        self.service = DiagnosticService()
        self.addCleanup(self.service.disconnect)
        self.service.connect(ConnectionConfig(port=self.adapter.port))

    def test_poll_multiple_ecus_no_zero_on_missing(self):
        snapshot = self.service.poll()
        rpm = {r["ecu"]: r["value"] for r in snapshot["readings"] if r["pid"] == "0C"}
        self.assertEqual(rpm, {"7E8": 1726, "7E9": 1000})
        self.adapter.responses["010C"] = "NO DATA\r>"
        snapshot = self.service.poll()
        for reading in snapshot["readings"]:
            if reading["pid"] == "0C":
                self.assertEqual(reading["status"], "Indisponível")
                self.assertTrue(reading["stale"])
                self.assertIsNotNone(reading["timestamp"])
                self.assertNotEqual(reading["value"], 0)

    def test_codes_unknown_and_queries_failed(self):
        snapshot = self.service.read_codes()
        unknown = next(c for c in snapshot["codes"] if c["code"] == "U0123")
        self.assertEqual(unknown["description"], "Descrição não disponível")
        self.adapter.responses["03"] = "CAN ERROR\r>"
        snapshot = self.service.read_codes()
        self.assertEqual(snapshot["code_queries"]["Confirmado"]["status"], "Falha de consulta")

    def test_freeze_frame(self):
        snapshot = self.service.read_freeze_frame()
        self.assertEqual(snapshot["freeze_codes"], {"7E8": ["P0300"]})
        self.assertEqual(len(snapshot["freeze_frame"]), 3)

    def test_real_vehicle_clear_rejected_before_command(self):
        self.service.session.simulation = False
        with self.assertRaises(TransportError):
            self.service.clear_codes()
        self.assertNotIn("04", self.adapter.commands)

    def test_disconnect_preserves_values_as_old(self):
        self.service.poll()
        snapshot = self.service.disconnect()
        self.assertTrue(all(r["status"] == "Desactualizado" for r in snapshot["readings"] if r["value"] is not None))
