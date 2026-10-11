from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


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


@dataclass
class Reading:
    pid: str
    name: str
    unit: str
    ecu: str
    value: float | None = None
    status: str = "Nao consultado"
    timestamp: str | None = None
    detail: str = ""


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
    ecu_status: str = "Nao consultada"
    supported: dict[str, list[int]] = field(default_factory=dict)
    readings: list[Reading] = field(default_factory=list)
    codes: list[TroubleCode] = field(default_factory=list)
    code_queries: dict = field(default_factory=dict)
    freeze_frame: list[Reading] = field(default_factory=list)
    freeze_status: str = "Nao consultado"
    freeze_codes: dict[str, list[str]] = field(default_factory=dict)
    symptoms: str = ""
    analysis: dict | None = None
    analysis_input: dict | None = None
    clear_status: str = "Nao solicitada"

    def to_dict(self) -> dict:
        return asdict(self)
