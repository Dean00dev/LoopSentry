from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eval.run import (
    DEFAULT_CORPUS,
    MANIFEST,
    benchmark,
    evaluate,
    expand_case,
    load_cases,
    main,
    verify_manifest,
)


class EvaluationTests(unittest.TestCase):
    def test_manifest_binds_versioned_corpus(self):
        receipt = verify_manifest(DEFAULT_CORPUS)

        self.assertEqual(receipt["cases"], 32)
        self.assertEqual(receipt["labels"]["pathological"], 12)
        self.assertEqual(receipt["labels"]["benign"], 16)
        self.assertEqual(receipt["labels"]["ambiguous"], 4)

    def test_current_corpus_has_no_labelled_expectation_mismatches(self):
        report = evaluate(load_cases(DEFAULT_CORPUS))

        self.assertEqual(report["totals"]["mismatches"], 0)
        self.assertEqual(report["rates"]["pathological_detection"], 1.0)
        self.assertEqual(report["rates"]["benign_false_positive"], 0.0)
        self.assertEqual(report["rates"]["ambiguous_flagged"], 1.0)
        self.assertEqual(report["latency_units"]["max"], 128)

    def test_cycle_recipe_reports_prefix_as_loop_start(self):
        units, loop_start = expand_case(
            {
                "id": "example",
                "recipe": "cycle",
                "prefix": ["healthy"],
                "prefix_range": {"prefix": "context", "count": 2},
                "cycle": ["A", "B"],
                "repeats": 2,
                "suffix": ["after"],
            }
        )

        self.assertEqual(loop_start, 3)
        self.assertEqual(
            units,
            ["healthy", "context-0", "context-1", "A", "B", "A", "B", "after"],
        )

    def test_manifest_detects_corpus_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "v0.2.0.jsonl"
            manifest = root / "MANIFEST.json"
            corpus.write_bytes(DEFAULT_CORPUS.read_bytes() + b"\n")
            manifest.write_bytes(MANIFEST.read_bytes())

            with self.assertRaisesRegex(ValueError, "SHA-256"):
                verify_manifest(corpus, manifest)

    def test_loader_rejects_duplicate_ids(self):
        row = {
            "id": "duplicate",
            "label": "benign",
            "class": "example",
            "expected": "clear",
            "recipe": "literal",
            "units": ["a"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "duplicates.jsonl"
            corpus.write_text(
                json.dumps(row) + "\n" + json.dumps(row) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_cases(corpus)

    def test_loader_rejects_label_expectation_mismatch(self):
        row = {
            "id": "inflated-result",
            "label": "benign",
            "class": "example",
            "expected": "flag",
            "recipe": "literal",
            "units": ["x"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "mismatch.jsonl"
            corpus.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match label"):
                load_cases(corpus)

    def test_loader_rejects_empty_cycle(self):
        row = {
            "id": "empty",
            "label": "ambiguous",
            "class": "example",
            "expected": "observe",
            "recipe": "cycle",
            "cycle": [],
            "repeats": 8,
        }
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "empty.jsonl"
            corpus.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                load_cases(corpus)

    def test_loader_rejects_invalid_loop_start(self):
        row = {
            "id": "bad-start",
            "label": "benign",
            "class": "example",
            "expected": "clear",
            "recipe": "literal",
            "units": ["x"],
            "loop_start": 2,
        }
        with tempfile.TemporaryDirectory() as temporary:
            corpus = Path(temporary) / "bad-start.jsonl"
            corpus.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside expanded units"):
                load_cases(corpus)

    def test_benchmark_is_informational_and_bounded(self):
        report = benchmark(units=500, observations=2)

        self.assertFalse(report["timing_is_ci_gate"])
        self.assertEqual(report["retained_units_after_run"], 500)
        self.assertGreater(report["detector_ns_per_unit"]["median"], 0)

    def test_command_writes_machine_readable_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            exit_code = main(
                [
                    "--json-output",
                    str(output),
                    "--benchmark-units",
                    "200",
                    "--benchmark-observations",
                    "1",
                    "--fail-on-mismatch",
                ]
            )
            report = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["totals"]["mismatches"], 0)
        self.assertTrue(all("units" not in row for row in report["cases"]))


if __name__ == "__main__":
    unittest.main()
