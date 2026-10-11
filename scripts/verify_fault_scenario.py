"""Valida o cenario ELM real e a janela; Gemini nunca usa a rede."""

import argparse
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root / "tests"))
from test_fault_scenario import FaultScenarioTests


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, help="Porta livre para a instancia temporaria; omitir usa porta livre automatica.")
    args = parser.parse_args()
    if args.port is not None and not 1 <= args.port <= 65535:
        parser.error("A porta deve estar entre 1 e 65535.")
    FaultScenarioTests.port_override = args.port
    FaultScenarioTests.require_emulator = True
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(FaultScenarioTests),
    )
    raise SystemExit(not result.wasSuccessful())
