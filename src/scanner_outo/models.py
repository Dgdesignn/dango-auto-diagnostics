from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

NOT_QUERIED = "Não consultado"
QUERYING = "Consulta em curso"
EMPTY_CODES = "Nenhum código devolvido"
UNAVAILABLE = "Indisponível"
QUERY_FAILED = "Falha de consulta"
COMPLETE = "Consulta concluída"
AVAILABLE = "Disponível"
STALE = "Desactualizado"


class OriginError(ValueError):
    """A origem da sessão está ausente ou contradiz a ligação capturada."""


def origin_label(simulation: bool) -> str:
    if type(simulation) is not bool:
        raise OriginError("Origem da sessão inválida; confirme emulador ou veículo real.")
    return "Emulador / simulação" if simulation else "Veículo real"


def session_origin(session: dict) -> str:
    label = origin_label(session.get("simulation"))
    connection = session.get("connection", {})
    if "simulation" in connection and (
        type(connection["simulation"]) is not bool or connection["simulation"] != session["simulation"]
    ):
        raise OriginError("Origem da sessão e da ligação incompatíveis; confirme antes de guardar ou analisar.")
    return label


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConnectionConfig:
    kind: str = "TCP"
    host: str = "127.0.0.1"
    port: int = 35000
    serial_port: str = ""
    baudrate: int = 38400
    simulation: bool = True
    timeout: float = 4.0

    def __post_init__(self) -> None:
        origin_label(self.simulation)


@dataclass
class Reading:
    pid: str
    name: str
    unit: str
    ecu: str
    value: float | None = None
    status: str = NOT_QUERIED
    timestamp: str | None = None
    detail: str = ""
    stale: bool = False


@dataclass
class TroubleCode:
    code: str
    description: str
    status: str
    ecu: str


@dataclass
class Session:
    created_at: str = field(default_factory=now_iso)
    simulation: bool = True
    connection: dict = field(default_factory=dict)
    adapter_status: str = "Desligado"
    ecu_status: str = "Não consultada"
    supported: dict[str, list[int]] = field(default_factory=dict)
    readings: list[Reading] = field(default_factory=list)
    codes: list[TroubleCode] = field(default_factory=list)
    code_queries: dict = field(default_factory=lambda: {kind: {"status": NOT_QUERIED} for kind in ("Confirmado", "Pendente")})
    freeze_frame: list[Reading] = field(default_factory=list)
    freeze_status: str = NOT_QUERIED
    freeze_detail: str = ""
    freeze_codes: dict[str, list[str]] = field(default_factory=dict)
    symptoms: str = ""
    analysis: dict | None = None
    analysis_input: dict | None = None
    clear_status: str = "Não solicitada"

    def to_dict(self) -> dict:
        return asdict(self)
