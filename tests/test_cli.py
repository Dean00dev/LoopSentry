from __future__ import annotations

import io
import json
import sys
import unittest
from unittest.mock import patch

from loopsentry.cli import (
    EXIT_CLEAR,
    EXIT_FLAG,
    EXIT_TERMINATE_ELIGIBLE,
    iter_units,
    main,
)


class IterUnitsTests(unittest.TestCase):
    def test_character_word_and_line_modes(self):
        self.assertEqual(list(iter_units(io.StringIO("a b\n"), "characters")), list("a b\n"))
        self.assertEqual(list(iter_units(io.StringIO("a  b\nc"), "words")), ["a", "b", "c"])
        self.assertEqual(list(iter_units(io.StringIO("a\r\nb\n"), "lines")), ["a", "b"])

    def test_jsonl_mode_canonicalizes_key_order(self):
        units = list(iter_units(io.StringIO('{"b":2,"a":1}\n{"a":1,"b":2}\n'), "jsonl"))
        self.assertEqual(units, ['{"a":1,"b":2}', '{"a":1,"b":2}'])

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            list(iter_units(io.StringIO("x"), "unknown"))


class CommandLineTests(unittest.TestCase):
    def run_cli(self, argv, stdin):
        stdout = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(stdin)), patch.object(sys, "stdout", stdout):
            code = main(argv)
        return code, json.loads(stdout.getvalue())

    def test_scan_returns_content_free_flag_receipt(self):
        code, receipt = self.run_cli(
            [
                "scan",
                "--unit",
                "words",
                "--min-repeats",
                "2",
                "--max-period",
                "1",
                "--max-window",
                "2",
                "--min-observed-units",
                "2",
            ],
            "secret secret secret",
        )

        self.assertEqual(code, EXIT_FLAG)
        self.assertTrue(receipt["detected"])
        self.assertEqual(receipt["detection"]["outcome"], "flag")
        self.assertNotIn("secret", str(receipt))

    def test_scan_can_wait_for_termination_eligible(self):
        code, receipt = self.run_cli(
            [
                "scan",
                "--min-repeats",
                "2",
                "--terminate-repeats",
                "3",
                "--max-period",
                "1",
                "--max-window",
                "3",
                "--min-observed-units",
                "1",
                "--stop-on",
                "terminate_eligible",
            ],
            "x x x x",
        )

        self.assertEqual(code, EXIT_TERMINATE_ELIGIBLE)
        self.assertEqual(receipt["detection"]["repeats"], 3)

    def test_scan_clear_returns_zero(self):
        code, receipt = self.run_cli(
            [
                "scan",
                "--min-repeats",
                "2",
                "--max-period",
                "1",
                "--max-window",
                "2",
                "--min-observed-units",
                "1",
            ],
            "a b c d",
        )

        self.assertEqual(code, EXIT_CLEAR)
        self.assertFalse(receipt["detected"])
        self.assertIsNone(receipt["detection"])

    def test_jsonl_objects_can_be_compared_without_raw_object_retention(self):
        code, receipt = self.run_cli(
            [
                "scan",
                "--unit",
                "jsonl",
                "--min-repeats",
                "2",
                "--max-period",
                "1",
                "--max-window",
                "2",
                "--min-observed-units",
                "1",
            ],
            '{"tool":"search","attempt":1}\n{"attempt":1,"tool":"search"}\n',
        )

        self.assertEqual(code, EXIT_FLAG)
        self.assertTrue(receipt["detected"])
        self.assertNotIn("search", str(receipt))


if __name__ == "__main__":
    unittest.main()
