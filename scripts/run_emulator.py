"""Inicia car ou P0301 com descoberta automatica do ambiente do emulador."""

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.emulator_environment import ROOT, find_emulator_python


def main() -> int:
    try:
        interpreter = find_emulator_python()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if interpreter is None:
        print("Emulador nao encontrado. Prepare simulador_scanner/.venv ou defina ELM327_PYTHON.", file=sys.stderr)
        return 1
    command = [str(interpreter), "-X", "utf8", "-u", str(ROOT / "scripts/run_fault_emulator.py"),
               "--scenario", "car", *sys.argv[1:]]
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
