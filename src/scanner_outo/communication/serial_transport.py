from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

import serial
from serial.tools import list_ports

from scanner_outo.communication.base import ElmTransport, TransportError, TransportTimeout, TransportDisconnected


def available_ports() -> list[str]:
    return [p.device for p in list_ports.comports()]


@dataclass
class SerialElmTransport(ElmTransport):
    port: str
    baudrate: int = 38400
    timeout_seconds: float = 3.0
    _serial: serial.Serial | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def open(self) -> None:
        if self._serial is not None:
            return
        try:
            self._serial = serial.serial_for_url(
                self.port, baudrate=self.baudrate, timeout=0.1, write_timeout=self.timeout_seconds,
            )
        except (serial.SerialException, OSError) as exc:
            raise TransportDisconnected(f"Não foi possível abrir a porta {self.port}.") from exc

    def close(self) -> None:
        port, self._serial = self._serial, None
        if port is not None:
            port.close()

    def request(self, command: str) -> str:
        if not command.strip() or any(c in command for c in "\r\n"):
            raise TransportError("Comando ELM327 inválido.")
        with self._lock:
            port = self._serial
            if port is None:
                raise TransportDisconnected("Porta serial desligada.")
            try:
                port.write(command.strip().encode("ascii") + b"\r")
                deadline = time.monotonic() + self.timeout_seconds
                response = bytearray()
                while time.monotonic() < deadline:
                    response.extend(port.read(max(1, min(port.in_waiting, 4096))))
                    if len(response) > 65536:
                        raise TransportError("Resposta serial excede o limite de 64 KiB.")
                    if b">" in response:
                        return bytes(response[:response.index(b">") + 1]).decode("ascii", errors="replace")
                raise TransportTimeout("Tempo esgotado na porta serial; volte a ligar.")
            except (serial.SerialException, OSError) as exc:
                self.close()
                raise TransportDisconnected("Ligação serial interrompida.") from exc
            except TransportError:
                self.close()
                raise
