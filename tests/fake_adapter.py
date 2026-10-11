from __future__ import annotations

import socket
import threading
import time


class FakeAdapter:
    """Servidor controlado; nunca simula um teste de hardware fisico."""

    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(5)
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.stop = threading.Event()
        self.commands = []
        self.delay = 0
        self.responses = {
            "ATZ": "ELM327 v1.5\r>",
            "ATE0": "OK\r>", "ATL0": "OK\r>", "ATH0": "OK\r>",
            "ATH1": "OK\r>", "ATSP0": "OK\r>",
            "ATSH7E0": "OK\r>", "ATSH7E1": "OK\r>", "ATSH7DF": "OK\r>",
            "0100": "7E8 06 41 00 08 18 00 00\r7E9 06 41 00 00 18 00 00\r>",
            "010C": "7E8 04 41 0C 1A F8\r7E9 04 41 0C 0F A0\r>",
            "0105": "7E8 03 41 05 7B\r>",
            "010D": "7E8 03 41 0D 32\r7E9 03 41 0D 30\r>",
            "03": "7E8 05 43 03 00 C1 23\r7E9 03 43 00 00\r>",
            "07": "7E8 03 47 01 00\r7E9 03 47 00 00\r>",
            "020000": "7E8 07 42 00 00 08 18 00 00\r>",
            "020200": "7E8 05 42 02 00 03 00\r>",
            "020C00": "7E8 05 42 0C 00 1A F8\r>",
            "020500": "7E8 04 42 05 00 7B\r>",
            "020D00": "7E8 04 42 0D 00 32\r>",
        }
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                connection.settimeout(0.1)
                buffer = b""
                while not self.stop.is_set():
                    try:
                        chunk = connection.recv(4096)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\r" in buffer:
                        command, buffer = buffer.split(b"\r", 1)
                        text = command.decode().strip().upper()
                        self.commands.append(text)
                        if self.delay:
                            time.sleep(self.delay)
                        try:
                            connection.sendall(self.responses.get(text, "NO DATA\r>").encode())
                        except OSError:
                            break

    def close(self):
        self.stop.set()
        self.listener.close()
        self.thread.join(2)
