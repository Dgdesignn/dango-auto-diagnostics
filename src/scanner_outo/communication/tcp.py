from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field

from scanner_outo.communication.base import ElmTransport, TransportError, TransportTimeout, TransportDisconnected


@dataclass
class TcpElmTransport(ElmTransport):
    host: str = "127.0.0.1"
    port: int = 35000
    timeout_seconds: float = 3.0
    _socket: socket.socket | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def open(self) -> None:
        if self._socket is not None:
            return
        try:
            self._socket = socket.create_connection((self.host, self.port), self.timeout_seconds)
        except OSError as exc:
            self.close()
            raise TransportDisconnected(
                f"Nao foi possivel ligar a {self.host}:{self.port}. Verifique o adaptador ou emulador."
            ) from exc

    def close(self) -> None:
        connection, self._socket = self._socket, None
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    def request(self, command: str) -> str:
        if not command.strip() or any(c in command for c in "\r\n"):
            raise TransportError("Comando ELM327 invalido.")
        with self._lock:
            connection = self._socket
            if connection is None:
                raise TransportDisconnected("Transporte TCP desligado.")
            deadline = time.monotonic() + self.timeout_seconds
            response = bytearray()
            try:
                connection.settimeout(self.timeout_seconds)
                connection.sendall(command.strip().encode("ascii") + b"\r")
                while b">" not in response:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    connection.settimeout(remaining)
                    chunk = connection.recv(4096)
                    if not chunk:
                        raise TransportDisconnected("Ligacao TCP fechada pelo adaptador.")
                    response.extend(chunk)
                    if len(response) > 65536:
                        raise TransportError("Resposta ELM327 excede o limite de 64 KiB.")
                return bytes(response[:response.index(b">") + 1]).decode("ascii", errors="replace")
            except TimeoutError as exc:
                self.close()
                raise TransportTimeout("Tempo esgotado; ligacao fechada para evitar respostas atrasadas.") from exc
            except OSError as exc:
                self.close()
                raise TransportDisconnected("Falha na ligacao TCP ao adaptador.") from exc
            except TransportError:
                self.close()
                raise
