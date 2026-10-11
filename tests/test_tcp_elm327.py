from __future__ import annotations

import socket
import threading
import unittest
from contextlib import closing

from scanner_outo.communication import TcpElmTransport
from scanner_outo.diagnostics import Elm327Client


def free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class FakeElmServer(threading.Thread):
    def __init__(self, port: int) -> None:
        super().__init__(daemon=True)
        self.port = port
        self.ready = threading.Event()

    def run(self) -> None:
        responses = {
            "ATZ": "ELM327 v1.5\r>",
            "ATE0": "OK\r>",
            "ATL0": "OK\r>",
            "ATH0": "OK\r>",
            "ATSP0": "OK\r>",
            "010C": "41 0C 1A F8\r>",
        }
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", self.port))
            server.listen(1)
            self.ready.set()
            conn, _addr = server.accept()
            with conn:
                buffer = b""
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\r" in buffer:
                        raw_command, buffer = buffer.split(b"\r", 1)
                        command = raw_command.decode("ascii").strip().upper()
                        conn.sendall(responses.get(command, "NO DATA\r>").encode("ascii"))


class TcpElmTransportTests(unittest.TestCase):
    def test_reads_rpm_over_tcp(self) -> None:
        port = free_port()
        server = FakeElmServer(port)
        server.start()
        self.assertTrue(server.ready.wait(timeout=2))

        with TcpElmTransport("127.0.0.1", port, timeout_seconds=2) as transport:
            client = Elm327Client(transport)
            client.initialize()
            result, rpm = client.read_rpm()

        self.assertEqual(result.command, "010C")
        self.assertEqual(result.response, "41 0C 1A F8\r>")
        self.assertEqual(rpm, 1726)


if __name__ == "__main__":
    unittest.main()

