"""Temporal metadata for immutable analysis snapshots and cache equivalence."""

from copy import deepcopy
from datetime import datetime, timezone

from scanner_outo.models import AVAILABLE


def age_seconds(timestamp, instant: datetime) -> float | None:
    try:
        parsed = datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:
            return None
        age = (instant - parsed).total_seconds()
        return round(age, 3) if age >= 0 else None
    except (TypeError, ValueError):
        return None


def age_band(age: float | None, recent: float = 10) -> str:
    if age is None:
        return "Instante desconhecido"
    if age <= recent:
        return "Recente"
    if age <= 60:
        return "Até 1 minuto"
    if age <= 300:
        return "Até 5 minutos"
    return "Mais de 5 minutos"


def reading_validity(reading: dict, instant: datetime, connected: bool, recent: float = 10) -> dict:
    result = deepcopy(reading)
    age = age_seconds(reading.get("timestamp"), instant)
    status = reading.get("status", "Não consultado")
    if reading.get("value") is None:
        validity = status
    elif status != AVAILABLE:
        validity = status
    elif reading.get("stale") or not connected or age is None or age > recent:
        validity = "Desactualizado"
    else:
        validity = "Recente"
    result.update(idade_segundos=age, faixa_temporal=age_band(age, recent), validade=validity)
    return result


def equivalent_data(value):
    # Exact clocks are omitted only AFTER validity and age bands have been captured.
    ignored = {"timestamp", "attempted_at", "idade_segundos", "capturado_em"}
    if isinstance(value, dict):
        return {key: equivalent_data(item) for key, item in value.items() if key not in ignored}
    if isinstance(value, list):
        return [equivalent_data(item) for item in value]
    return value
