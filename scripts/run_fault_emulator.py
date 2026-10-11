"""Launcher do cenario externo, usando a API do ELM327-emulator 4.0.0."""

from __future__ import annotations

import argparse
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import socket
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scenarios.rough_idle import ObdMessage, SCENARIO_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=35000)
    parser.add_argument("--stop-after", type=float, help="Terminar apos N segundos (testes).")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("A porta deve estar entre 1 e 65535.")
    if args.stop_after is not None and args.stop_after <= 0:
        parser.error("--stop-after deve ser positivo.")
    try:
        installed = version("ELM327-emulator")
    except PackageNotFoundError:
        print("Execute com o Python do ambiente que tem ELM327-emulator instalado.", file=sys.stderr)
        return 1
    if installed != "4.0.0":
        print(f"Versao {installed} nao validada; este launcher exige 4.0.0.", file=sys.stderr)
        return 1
    from elm import Elm

    # A verificacao previa evita iniciar outra instancia numa porta ocupada.
    try:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", args.port))
    except OSError:
        print(f"Porta {args.port} ocupada/indisponivel. Pare manualmente a outra instancia.", file=sys.stderr)
        return 1
    emulator = Elm(net_port=args.port, net_interface="127.0.0.1", batch_mode=True)
    # Mantem os comandos AT; nao herda dados OBD de default/car nem altera globais.
    emulator.ObdMessage = {
        "AT": deepcopy(emulator.ObdMessage["AT"]), "default": {},
        **deepcopy(ObdMessage),
    }
    emulator.set_sorted_obd_msg(SCENARIO_NAME)
    emulator.choice_mode = emulator.Choice.SEQUENTIAL
    emulator.choice_weights = [1]
    try:
        with emulator:
            deadline = time.monotonic() + 5
            while emulator.threadState == emulator.THREAD.STARTING:
                if time.monotonic() >= deadline:
                    print("Timeout ao iniciar o emulador.", file=sys.stderr)
                    return 1
                time.sleep(0.05)
            if emulator.threadState != emulator.THREAD.ACTIVE:
                print("O emulador nao conseguiu abrir a ligacao TCP.", file=sys.stderr)
                return 1
            print(f"READY ELM327-emulator {installed}: {SCENARIO_NAME} em 127.0.0.1:{args.port}", flush=True)
            print("P0301 confirmado; RPM 680-820; 88 graus Celsius; 0 km/h. Ctrl+C para parar.", flush=True)
            end = time.monotonic() + args.stop_after if args.stop_after else None
            while emulator.threadState == emulator.THREAD.ACTIVE:
                if end is not None and time.monotonic() >= end:
                    return 0
                time.sleep(0.1)
            return 1
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
