"""Launcher de car/P0301, usando a API do ELM327-emulator 4.0.0."""

from __future__ import annotations

import argparse
from contextlib import chdir
from copy import deepcopy
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import os
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scenarios.rough_idle import ObdMessage, SCENARIO_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=35000)
    parser.add_argument("--scenario", choices=("car", SCENARIO_NAME), default=SCENARIO_NAME)
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
    if args.scenario == SCENARIO_NAME:
        # Mantem AT, sem herdar dados OBD de default/car nem alterar globais.
        emulator.ObdMessage = {
            "AT": deepcopy(emulator.ObdMessage["AT"]), "default": {},
            **deepcopy(ObdMessage),
        }
    else:
        emulator.ObdMessage = deepcopy(emulator.ObdMessage)
    emulator.set_sorted_obd_msg(args.scenario)
    emulator.choice_mode = emulator.Choice.SEQUENTIAL
    emulator.choice_weights = [1]
    log_dir = ROOT / "logs/emulator"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"elm-{args.port}.log"
    previous_log_config = os.environ.get("ELM_LOG_CFG")
    previous_log_file = os.environ.get("SCANNER_EMULATOR_LOG_FILE")
    os.environ["ELM_LOG_CFG"] = str(ROOT / "config/elm-logging.json")
    os.environ["SCANNER_EMULATOR_LOG_FILE"] = str(log_path)
    try:
        return run(emulator, args, installed, log_path)
    except KeyboardInterrupt:
        return 0
    finally:
        if previous_log_config is None:
            os.environ.pop("ELM_LOG_CFG", None)
        else:
            os.environ["ELM_LOG_CFG"] = previous_log_config
        if previous_log_file is None:
            os.environ.pop("SCANNER_EMULATOR_LOG_FILE", None)
        else:
            os.environ["SCANNER_EMULATOR_LOG_FILE"] = previous_log_file


def run(emulator, args, installed: str, log_path: Path) -> int:
    with chdir(ROOT), emulator:
        deadline = time.monotonic() + 5
        while emulator.threadState == emulator.THREAD.STARTING:
            if time.monotonic() >= deadline:
                print("Timeout ao iniciar o emulador.", file=sys.stderr)
                return 1
            time.sleep(0.05)
        if emulator.threadState != emulator.THREAD.ACTIVE:
            print("O emulador nao conseguiu abrir a ligacao TCP.", file=sys.stderr)
            return 1
        print(f"READY ELM327-emulator {installed}: {args.scenario} em 127.0.0.1:{args.port}", flush=True)
        print(f"Log: {log_path}", flush=True)
        if args.scenario == SCENARIO_NAME:
            print("P0301 confirmado; RPM 680-820; 88 graus Celsius; 0 km/h.", flush=True)
        print("Ctrl+C para parar.", flush=True)
        end = time.monotonic() + args.stop_after if args.stop_after else None
        while emulator.threadState == emulator.THREAD.ACTIVE:
            if end is not None and time.monotonic() >= end:
                return 0
            time.sleep(0.1)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
