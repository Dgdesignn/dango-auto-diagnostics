"""Run the real native Qt workflow and capture the requested logical sizes."""
import argparse
import os
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", choices=("1", "1.25", "1.5"), default="1")
    args = parser.parse_args()
    os.environ["QT_SCALE_FACTOR"] = args.scale
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    suite = unittest.defaultTestLoader.loadTestsFromName(
        "test_stitch_ui.StitchUiTests.test_full_workflow_through_sidebar_and_visual_captures")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
