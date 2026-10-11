"""Canal HTTP local separado de OBD, com pedidos limitados e autenticados."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
from threading import Event, Thread


class ControlServer:
    def __init__(self, state, port: int, token: str):
        self.stop = Event()
        self.state = state
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(2)

            def do_POST(self):
                try:
                    if self.path != "/control" or not hmac.compare_digest(
                        self.headers.get("Authorization", ""), "Bearer " + token
                    ):
                        self.send_error(403)
                        return
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= size <= 1024 or self.headers.get("Transfer-Encoding"):
                        raise ValueError("Tamanho de pedido invalido.")
                    request = json.loads(self.rfile.read(size))
                    if not isinstance(request, dict) or set(request) != {"action"}:
                        raise ValueError("Pedido invalido.")
                    action = request["action"]
                    if not isinstance(action, str) or action not in ("status", "cycle", "resolve", "reset", "shutdown"):
                        raise ValueError("Accao invalida.")
                    result = state.snapshot() if action == "shutdown" else state.control(action)
                    payload = json.dumps({"ok": True, "state": result}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    if action == "shutdown":
                        owner.stop.set()
                except (ValueError, TypeError, OSError):
                    self.send_error(400, "Pedido de controlo invalido")

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.thread = Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
