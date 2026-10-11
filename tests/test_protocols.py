import unittest

from scanner_outo.diagnostics.obd import (
    parse_frames, decode_pid, decode_dtcs, decode_supported,
    ObdDecodeError, NoDataError, AdapterError, DTC_DESCRIPTIONS,
)


class ProtocolTests(unittest.TestCase):
    def test_parameters(self):
        for response, pid, expected in (("41 0C 1A F8", 12, 1726), ("41 05 7B", 5, 83), ("41 0D 32", 13, 50)):
            self.assertEqual(decode_pid(parse_frames(response)[0], pid), expected)

    def test_echo_search_and_ecus(self):
        frames = parse_frames("010C\rSEARCHING...\r7E8 04 41 0C 1A F8\r7E9 04 41 0C 0F A0\r>", "010C")
        self.assertEqual([(f.ecu, decode_pid(f, 12)) for f in frames], [("7E8", 1726), ("7E9", 1000)])

    def test_compact_29_bit_header(self):
        frame = parse_frames("18DAF110 04410C1AF8\r>")[0]
        self.assertEqual(frame.ecu, "18DAF110")
        self.assertEqual(decode_pid(frame, 12), 1726)

    def test_invalid_incomplete_and_mismatch(self):
        for response in ("41 0C 1A", "41 0D 1A F8", "42 0C 1A F8", "41 0C 1A F8 00"):
            with self.assertRaises(ObdDecodeError):
                decode_pid(parse_frames(response)[0], 12)
        for response in ("7E8 04 41 0C 1A", "garbage", "41 0"):
            with self.assertRaises(ObdDecodeError):
                parse_frames(response)

    def test_distinct_no_data_and_adapter_error(self):
        with self.assertRaises(NoDataError):
            parse_frames("NO DATA\r>")
        with self.assertRaises(AdapterError):
            parse_frames("CAN ERROR\r>")

    def test_no_cross_ecu_assembly(self):
        with self.assertRaises(ObdDecodeError):
            frames = parse_frames("7E8 03 41 0C 1A\r7E9 01 F8\r>")
            decode_pid(frames[0], 12)

    def test_supported_map(self):
        supported = decode_supported(parse_frames("41 00 08 18 00 00")[0])
        self.assertEqual(supported, {5, 12, 13})

    def test_known_unknown_codes(self):
        codes = decode_dtcs(parse_frames("43 03 00 C1 23 00 00")[0], 3)
        self.assertEqual(codes, ["P0300", "U0123"])
        self.assertIn("P0300", DTC_DESCRIPTIONS)
        self.assertNotIn("U0123", DTC_DESCRIPTIONS)

    def test_can_count_and_no_codes(self):
        self.assertEqual(decode_dtcs(parse_frames("7E8 02 43 00")[0], 3), [])
        self.assertEqual(decode_dtcs(parse_frames("7E8 06 43 02 03 00 C1 23")[0], 3), ["P0300", "U0123"])
        with self.assertRaises(ObdDecodeError):
            decode_dtcs(parse_frames("43 02 03 00")[0], 3)

    def test_interleaved_multiframe(self):
        response = "7E8 10 09 43 03 00 03 01 03\r7E9 03 43 01 00\r7E8 21 02 04 20 00 00 00 00\r>"
        frames = parse_frames(response)
        by_ecu = {f.ecu: decode_dtcs(f, 3) for f in frames}
        self.assertEqual(by_ecu["7E8"], ["P0300", "P0301", "P0302", "P0420"])
        self.assertEqual(by_ecu["7E9"], ["P0100"])

    def test_multiframe_incomplete_and_sequence(self):
        for response in ("7E8 10 09 43 03 00 03 01 03\r>", "7E8 10 09 43 03 00 03 01 03\r7E8 22 02 04 20\r>"):
            with self.assertRaises(ObdDecodeError):
                parse_frames(response)

    def test_freeze_frame(self):
        self.assertEqual(decode_pid(parse_frames("42 05 00 7B")[0], 5, 2), 83)
        with self.assertRaises(ObdDecodeError):
            decode_pid(parse_frames("42 05 01 7B")[0], 5, 2)
