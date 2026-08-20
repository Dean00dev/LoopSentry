from __future__ import annotations

import unittest
from itertools import product

from loopsentry import LoopSentry, Outcome


class LoopSentryTests(unittest.TestCase):
    def test_detects_single_unit_loop(self):
        guard = LoopSentry(min_repeats=8, max_period=1, max_window=8, min_observed_units=8)
        hit = guard.scan(["poem"] * 100)

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.period, 1)
        self.assertEqual(hit.repeats, 8)
        self.assertEqual(hit.reason, "exact_periodic_loop")
        self.assertEqual(hit.outcome, Outcome.FLAG)

    def test_detects_multi_unit_cycle_and_shortest_fundamental_period(self):
        guard = LoopSentry(min_repeats=4, max_period=4, max_window=16, min_observed_units=8)
        hit = guard.scan(["A", "B"] * 20)

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.period, 2)
        self.assertEqual(hit.matched_units, 8)

    def test_reports_observed_repeat_count_not_only_threshold(self):
        guard = LoopSentry(min_repeats=2, max_period=2, max_window=20, min_observed_units=1)
        hit = None
        for unit in ["A", "B"] * 5:
            hit = guard.push(unit)

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.period, 2)
        self.assertEqual(hit.repeats, 5)
        self.assertEqual(hit.matched_units, 10)
        self.assertEqual(hit.start_unit, 0)
        self.assertEqual(hit.end_unit, 10)

    def test_single_unit_pattern_wins_over_larger_periods(self):
        guard = LoopSentry(min_repeats=3, max_period=4, max_window=12, min_observed_units=3)
        hit = guard.scan(["same"] * 20)

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.period, 1)

    def test_prefix_is_excluded_from_detection_span(self):
        guard = LoopSentry(min_repeats=4, max_period=2, max_window=16, min_observed_units=1)
        hit = guard.scan(["prefix", "varies", "here", *(["A", "B"] * 4)])

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.start_unit, 3)
        self.assertEqual(hit.end_unit, 11)
        self.assertEqual(hit.matched_units, 8)

    def test_flag_escalates_only_at_termination_threshold(self):
        guard = LoopSentry(
            min_repeats=3,
            terminate_repeats=5,
            max_period=1,
            max_window=5,
            min_observed_units=1,
        )
        outcomes = [guard.push("x") for _ in range(5)]

        self.assertIsNone(outcomes[1])
        assert outcomes[2] is not None
        assert outcomes[3] is not None
        assert outcomes[4] is not None
        self.assertEqual(outcomes[2].outcome, Outcome.FLAG)
        self.assertEqual(outcomes[3].outcome, Outcome.FLAG)
        self.assertEqual(outcomes[4].outcome, Outcome.TERMINATE_ELIGIBLE)

    def test_scan_can_wait_for_termination_eligibility(self):
        guard = LoopSentry(
            min_repeats=2,
            terminate_repeats=4,
            max_period=1,
            max_window=4,
            min_observed_units=1,
        )
        hit = guard.scan(["x"] * 20, minimum_outcome=Outcome.TERMINATE_ELIGIBLE)

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.observed_units, 4)
        self.assertEqual(hit.repeats, 4)

    def test_scan_rejects_unreachable_or_continue_outcome(self):
        guard = LoopSentry()
        with self.assertRaisesRegex(ValueError, "terminate_repeats"):
            guard.scan(["x"] * 100, minimum_outcome=Outcome.TERMINATE_ELIGIBLE)
        with self.assertRaisesRegex(ValueError, "minimum_outcome"):
            guard.scan([], minimum_outcome=Outcome.CONTINUE)

    def test_does_not_flag_short_bounded_repetition_by_default(self):
        guard = LoopSentry()
        self.assertIsNone(guard.scan(["hello"] * 20))

    def test_does_not_flag_nonperiodic_text(self):
        guard = LoopSentry(min_observed_units=8)
        units = [
            "the",
            "quick",
            "brown",
            "fox",
            "jumps",
            "over",
            "the",
            "lazy",
            "dog",
            "then",
            "leaves",
            "quietly",
        ]
        self.assertIsNone(guard.scan(units))

    def test_cycle_larger_than_max_period_is_not_flagged(self):
        guard = LoopSentry(
            min_repeats=4,
            max_period=2,
            max_window=8,
            min_observed_units=1,
        )
        self.assertIsNone(guard.scan(["A", "B", "C"] * 20))

    def test_window_is_bounded_and_receipt_marks_lower_bound(self):
        guard = LoopSentry(
            min_repeats=2,
            max_period=1,
            max_window=2,
            min_observed_units=1,
        )
        hit = None
        for _ in range(100):
            hit = guard.push("x")

        self.assertEqual(guard.observed_units, 100)
        self.assertEqual(guard.retained_units, 2)
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.repeats, 2)
        self.assertTrue(hit.window_limited)
        self.assertEqual(hit.start_unit, 98)

    def test_clear_unit_clears_last_detection(self):
        guard = LoopSentry(
            min_repeats=2,
            max_period=1,
            max_window=2,
            min_observed_units=1,
        )
        self.assertIsNotNone(guard.scan(["x", "x"]))
        self.assertIsNotNone(guard.last_detection)
        self.assertIsNone(guard.push("different"))
        self.assertIsNone(guard.last_detection)

    def test_reset_clears_stream_state_but_keeps_configuration(self):
        guard = LoopSentry(
            min_repeats=2,
            max_period=1,
            max_window=2,
            min_observed_units=1,
        )
        guard.scan(["x", "x"])
        guard.reset()

        self.assertEqual(guard.observed_units, 0)
        self.assertEqual(guard.retained_units, 0)
        self.assertIsNone(guard.last_detection)
        self.assertEqual(guard.min_repeats, 2)

    def test_key_normalizes_mutable_events_before_retention(self):
        guard = LoopSentry(
            min_repeats=2,
            max_period=1,
            max_window=2,
            min_observed_units=1,
            key=lambda event: (event["tool"], event["status"]),
        )
        event = {"tool": "search", "status": "retry", "secret": "not retained"}
        hit = guard.scan([event, dict(event)])

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertNotIn("secret", str(hit.as_dict()))

    def test_unhashable_unit_is_rejected_without_advancing_state(self):
        guard = LoopSentry()
        with self.assertRaisesRegex(TypeError, "hashable"):
            guard.push(["mutable"])
        self.assertEqual(guard.observed_units, 0)
        self.assertEqual(guard.retained_units, 0)

    def test_unhashable_key_result_is_rejected(self):
        guard = LoopSentry(key=lambda value: [value])
        with self.assertRaisesRegex(TypeError, "hashable"):
            guard.push("x")

    def test_detection_receipt_contains_no_observed_content(self):
        guard = LoopSentry(
            min_repeats=2,
            max_period=1,
            max_window=2,
            min_observed_units=1,
        )
        hit = guard.scan(["private-value", "private-value"])

        self.assertIsNotNone(hit)
        assert hit is not None
        receipt = hit.as_dict()
        self.assertNotIn("private-value", str(receipt))
        self.assertEqual(receipt["period"], 1)
        self.assertEqual(receipt["start_unit"], 0)

    def test_legacy_min_observed_tokens_alias_remains_supported(self):
        guard = LoopSentry(
            min_repeats=2,
            max_period=1,
            max_window=2,
            min_observed_tokens=2,
        )
        hit = guard.scan(["x", "x"])

        self.assertIsNotNone(hit)
        self.assertEqual(guard.min_observed_tokens, 2)
        self.assertEqual(guard.observed_tokens, 2)
        assert hit is not None
        self.assertEqual(hit.observed_tokens, 2)

    def test_configuration_rejects_ambiguous_aliases(self):
        with self.assertRaisesRegex(ValueError, "not both"):
            LoopSentry(min_observed_units=1, min_observed_tokens=1)

    def test_configuration_rejects_invalid_values(self):
        invalid = (
            {"min_repeats": 1},
            {"max_period": 0},
            {"max_window": 0},
            {"min_observed_units": 0},
            {"min_repeats": True},
            {"max_period": 1.5},
            {"terminate_repeats": 7},
            {"max_period": 16, "max_window": 127},
            {"min_repeats": 2, "terminate_repeats": 4, "max_period": 2, "max_window": 7},
        )
        for configuration in invalid:
            with (
                self.subTest(configuration=configuration),
                self.assertRaises((TypeError, ValueError)),
            ):
                LoopSentry(**configuration)

    def test_configuration_rejects_noncallable_key(self):
        with self.assertRaisesRegex(TypeError, "callable"):
            LoopSentry(key="not-callable")

    def test_exhaustive_binary_suffixes_match_reference_detector(self):
        for length in range(1, 9):
            for sequence in product((0, 1), repeat=length):
                guard = LoopSentry(
                    min_repeats=2,
                    max_period=3,
                    max_window=8,
                    min_observed_units=1,
                )
                hit = None
                for unit in sequence:
                    hit = guard.push(unit)

                expected = _reference_suffix(sequence, min_repeats=2, max_period=3)
                if expected is None:
                    self.assertIsNone(hit, sequence)
                else:
                    self.assertIsNotNone(hit, sequence)
                    assert hit is not None
                    self.assertEqual((hit.period, hit.repeats), expected, sequence)


def _reference_suffix(sequence, *, min_repeats, max_period):
    for period in range(1, min(max_period, len(sequence) // min_repeats) + 1):
        pattern = sequence[-period:]
        repeats = 0
        cursor = len(sequence)
        while cursor >= period and sequence[cursor - period : cursor] == pattern:
            repeats += 1
            cursor -= period
        if repeats >= min_repeats:
            return period, repeats
    return None


if __name__ == "__main__":
    unittest.main()
