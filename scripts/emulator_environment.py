"""Descobre o Python do emulador sem depender de C:\\Py."""

from __future__ import annotations

import importlib.util
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]


def emulator_log_handler(filename: str, **options) -> RotatingFileHandler:
    path = Path(os.getenv("SCANNER_EMULATOR_LOG_FILE", str(ROOT / filename)))
    return RotatingFileHandler(path, **options)


def find_emulator_python(root: Path = ROOT, environ: Mapping[str, str] | None = None) -> Path | None:
    env = os.environ if environ is None else environ
    configured = env.get("ELM327_PYTHON", "").strip()
    if configured:
        path = Path(os.path.expandvars(configured)).expanduser()
        if not path.is_absolute():
            path = root / path
        if not path.is_file():
            raise FileNotFoundError("ELM327_PYTHON nao aponta para um ficheiro existente.")
        return path.resolve()
    relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    sibling = root.parent / "simulador_scanner" / ".venv" / relative
    if sibling.is_file():
        return sibling.resolve()
    if importlib.util.find_spec("elm") is not None:
        return Path(sys.executable).resolve()
    return None
