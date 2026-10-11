from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scanner_outo.communication import TcpElmTransport, TransportError
from scanner_outo.diagnostics import Elm327Client
from scanner_outo.diagnostics.obd import ObdDecodeError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Testa comunicacao ELM327 por TCP e descodifica RPM.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host TCP do ELM327-emulator.")
    parser.add_argument("--port", default=35000, type=int, help="Porta TCP do ELM327-emulator.")
    parser.add_argument("--timeout", default=3.0, type=float, help="Timeout em segundos.")
    return parser


def print_exchange(command: str, response: str) -> None:
    compact_response = response.replace("\r", "\\r").replace("\n", "\\n")
    print(f"Pedido : {command}")
    print(f"Resposta: {compact_response}")
    print()


def main() -> int:
    args = build_parser().parse_args()
    transport = TcpElmTransport(args.host, args.port, args.timeout)

    try:
        with transport:
            client = Elm327Client(transport)

            print(f"Ligado a ELM327 em {args.host}:{args.port}")
            print()

            for result in client.initialize():
                print_exchange(result.command, result.response)

            rpm_result, rpm = client.read_rpm()
            print_exchange(rpm_result.command, rpm_result.response)
            print(f"RPM descodificado: {rpm:.0f} rpm")
            return 0
    except (TransportError, ObdDecodeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

