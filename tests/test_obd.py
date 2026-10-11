from __future__ import annotations

import unittest

from scanner_outo.diagnostics.obd import decode_rpm


class DecodeRpmTests(unittest.TestCase):
    def test_decodes_spaced_response(self) -> None:
        self.assertEqual(decode_rpm("41 0C 1A F8\r>"), 1726)

    def test_decodes_compact_response(self) -> None:
        self.assertEqual(decode_rpm("410C1AF8\r>"), 1726)


if __name__ == "__main__":
    unittest.main()

