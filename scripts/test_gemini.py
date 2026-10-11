"""Valida Gemini com dados ficticios, sem expor a credencial local."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scanner_outo.config import Settings
from scanner_outo.gemini import AnalysisError, GeminiService, analysis_payload
from scanner_outo.models import AVAILABLE, Reading, Session
from scanner_outo.persistence import SessionStore


def main() -> int:
    settings = Settings.load()
    session = Session(
        simulation=True,
        ecu_status=AVAILABLE,
        readings=[Reading("0C", "RPM", "rpm", "7E8", 850.0, AVAILABLE)],
    )
    payload = analysis_payload(
        session.to_dict(),
        "Teste de integracao com dados ficticios. Nenhum veiculo real foi medido.",
    )
    service = GeminiService(settings, SessionStore(settings.data_dir / "sessions.sqlite3"))
    print(f"Modelo: {settings.model}")
    print(f"Chave configurada: {bool(settings.api_key)}")
    print(f"Limite diario: {settings.daily_limit}; intervalo minimo: {settings.minimum_interval}s")
    print("Pedido: " + json.dumps(payload, ensure_ascii=False))
    try:
        result = service.analyze(payload, settings.model)
    except AnalysisError as exc:
        print(f"Falha: {exc}")
        return 1
    print("Resposta validada: " + json.dumps(result, ensure_ascii=False, indent=2))
    cached = service.analyze(payload, settings.model)
    print(f"Segunda consulta em cache, sem nova chamada: {cached['cache']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
