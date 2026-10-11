from __future__ import annotations

from dataclasses import dataclass
import logging
import threading

from scanner_outo.communication.base import ElmTransport
from scanner_outo.diagnostics.obd import decode_rpm
from scanner_outo.diagnostics.obd import AdapterError


@dataclass
class ElmCommandResult:
    command: str
    response: str


class Elm327Client:
    """Cliente de alto nivel para comandos ELM327 e PIDs OBD-II."""

    def __init__(self, transport: ElmTransport) -> None:
        self._transport = transport
        self._lock = threading.RLock()

    def initialize(self) -> list[ElmCommandResult]:
        commands = ["ATZ", "ATE0", "ATL0", "ATH0", "ATSP0"]
        with self._lock:
            results = [self.send(command) for command in commands]
            for result in results[1:]:
                if "OK" not in result.response.upper():
                    raise AdapterError(f"O adaptador nao confirmou {result.command}.")
            return results

    def enable_headers(self) -> None:
        if "OK" not in self.send("ATH1").response.upper():
            raise AdapterError("O adaptador nao suporta identificacao de ECU (ATH1).")

    def send(self, command: str) -> ElmCommandResult:
        with self._lock:
            response = self._transport.request(command)
            logging.getLogger(__name__).info("ELM pedido=%s resposta=%r", command, response)
            return ElmCommandResult(command=command, response=response)

    def read_rpm(self) -> tuple[ElmCommandResult, float]:
        result = self.send("010C")
        return result, decode_rpm(result.response)

