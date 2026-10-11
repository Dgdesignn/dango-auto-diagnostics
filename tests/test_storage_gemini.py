import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scanner_outo.config import Settings
from scanner_outo.models import Session
from scanner_outo.persistence import SessionStore
from scanner_outo.gemini import GeminiService, AnalysisError, AnalysisQuotaError, analysis_payload, official_generate


VALID = {key: ["Exemplo de teste"] for key in ("factos_medidos", "hipoteses", "evidencias", "informacao_em_falta", "proximos_testes")}


class StorageGeminiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.store = SessionStore(self.path / "sessions.sqlite3")
        self.settings = Settings(data_dir=self.path, api_key="ficticia-para-teste", daily_limit=2, minimum_interval=10)
        self.payload = analysis_payload(Session().to_dict(), "motor irregular")

    def generate(self, *_args):
        return {"text": json.dumps(VALID), "tokens": {"entrada": 15, "saida": 20, "total": 35}}

    def test_save_open_export(self):
        snapshot = Session(symptoms="motor irregular").to_dict()
        session_id = self.store.save(snapshot)
        self.assertEqual(self.store.load(session_id), snapshot)
        self.assertEqual(self.store.list_sessions()[0]["id"], session_id)
        destination = self.path / "session.json"
        self.store.export(session_id, destination)
        self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), snapshot)

    def test_success_cache_without_second_call(self):
        calls = []
        def generate(*args):
            calls.append(1)
            return self.generate(*args)
        service = GeminiService(self.settings, self.store, generate, clock=lambda: 100)
        first = service.analyze(self.payload, "modelo-teste")
        second = service.analyze(self.payload, "modelo-teste")
        self.assertFalse(first["cache"])
        self.assertTrue(second["cache"])
        self.assertEqual(first["tokens"]["total"], 35)
        self.assertEqual(len(calls), 1)

    def test_missing_key(self):
        self.settings.api_key = ""
        with self.assertRaises(AnalysisError):
            GeminiService(self.settings, self.store, self.generate).analyze(self.payload, "test")

    def test_failed_call_does_not_expose_key(self):
        def fail(*_args):
            raise RuntimeError(self.settings.api_key)
        with self.assertRaises(AnalysisError) as error:
            GeminiService(self.settings, self.store, fail).analyze(self.payload, "test")
        self.assertNotIn(self.settings.api_key, str(error.exception))

    def test_quota(self):
        def quota(*_args):
            raise AnalysisQuotaError("Quota atingida")
        with self.assertRaises(AnalysisQuotaError):
            GeminiService(self.settings, self.store, quota).analyze(self.payload, "test")

    def test_invalid_response(self):
        for text in ("not JSON", "{}", json.dumps({**VALID, "comando": "04"})):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as temp:
                store = SessionStore(Path(temp) / "db.sqlite3")
                with self.assertRaises(AnalysisError):
                    GeminiService(self.settings, store, lambda *_: {"text": text}).analyze(self.payload, "test")

    def test_limits_count_failed_calls(self):
        clock = [100]
        service = GeminiService(self.settings, self.store, self.generate, lambda: clock[0])
        service.analyze(self.payload, "test1")
        with self.assertRaisesRegex(AnalysisError, "intervalo"):
            service.analyze(self.payload, "test2")
        clock[0] = 110
        service.analyze(self.payload, "test2")
        clock[0] = 120
        with self.assertRaisesRegex(AnalysisError, "diario"):
            service.analyze(self.payload, "test3")
        clock[0] = 86500
        service.analyze(self.payload, "test3")

    def test_failed_calls_still_consume_local_allowance(self):
        self.settings.daily_limit = 1
        def fail(*_args):
            raise AnalysisError("Indisponivel")
        service = GeminiService(self.settings, self.store, fail, lambda: 100)
        with self.assertRaisesRegex(AnalysisError, "Indisponivel"):
            service.analyze(self.payload, "test")
        with self.assertRaisesRegex(AnalysisError, "diario"):
            service.analyze(self.payload, "test2")

    def test_cache_keeps_states_and_model_in_key(self):
        self.settings.minimum_interval = 0
        service = GeminiService(self.settings, self.store, self.generate)
        first = service.analyze(self.payload, "test")
        payload = {**self.payload, "estado_ecu": "Comunicacao interrompida"}
        changed = service.analyze(payload, "test")
        self.assertFalse(first["cache"])
        self.assertFalse(changed["cache"])

    def test_payload_omits_identifiers_and_limits_size(self):
        session = Session(connection={"vin": "nao-enviar"}).to_dict()
        session["vin"] = "nao-enviar"
        self.assertNotIn("nao-enviar", json.dumps(analysis_payload(session, "sintomas")))
        with self.assertRaises(AnalysisError):
            analysis_payload(session, "x" * 4001)

    def test_official_error_mapping_without_secrets(self):
        class QuotaError(Exception):
            code = 429
        with patch("google.genai.Client", side_effect=QuotaError("segredo")):
            with self.assertRaises(AnalysisQuotaError) as error:
                official_generate(self.settings, "test", self.payload)
        self.assertNotIn("segredo", str(error.exception))
