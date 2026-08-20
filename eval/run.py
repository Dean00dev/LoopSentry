"""Evaluate LoopSentry against a versioned, class-stratified corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from time import perf_counter_ns
from typing import Any

from loopsentry import LoopSentry

ROOT = Path(__file__).resolve().parent
DEFAULT_CORPUS = ROOT / "corpus" / "v0.2.0.jsonl"
MANIFEST = ROOT / "corpus" / "MANIFEST.json"
ALLOWED_LABELS = {"pathological", "benign", "ambiguous"}
ALLOWED_EXPECTATIONS = {"flag", "clear", "observe"}
EXPECTATION_BY_LABEL = {
    "pathological": "flag",
    "benign": "clear",
    "ambiguous": "observe",
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    """Load and validate a JSONL corpus without silently skipping bad rows."""
    cases: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error.msg}") from error
            identifier = case.get("id")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError(f"{path}:{line_number}: case id must be a non-empty string")
            if identifier in identifiers:
                raise ValueError(f"{path}:{line_number}: duplicate case id: {identifier}")
            if case.get("label") not in ALLOWED_LABELS:
                raise ValueError(f"{path}:{line_number}: unsupported label")
            expected = case.get("expected")
            if expected not in ALLOWED_EXPECTATIONS:
                raise ValueError(f"{path}:{line_number}: unsupported expectation")
            if expected != EXPECTATION_BY_LABEL[case["label"]]:
                raise ValueError(
                    f"{path}:{line_number}: expectation does not match label {case['label']}"
                )
            if not isinstance(case.get("class"), str) or not case["class"]:
                raise ValueError(f"{path}:{line_number}: class must be a non-empty string")
            expected_period = case.get("expected_period")
            if expected_period is not None:
                _positive_int(expected_period, "expected_period")
            if case["label"] == "pathological" and expected_period is None:
                raise ValueError(f"{path}:{line_number}: pathological case needs expected_period")
            units, loop_start = expand_case(case)
            if not units:
                raise ValueError(f"{path}:{line_number}: expanded case is empty")
            if loop_start is not None and (
                isinstance(loop_start, bool)
                or not isinstance(loop_start, int)
                or loop_start < 0
                or loop_start >= len(units)
            ):
                raise ValueError(f"{path}:{line_number}: loop_start is outside expanded units")
            identifiers.add(identifier)
            cases.append(case)
    if not cases:
        raise ValueError(f"{path}: corpus is empty")
    return cases


def expand_case(case: dict[str, Any]) -> tuple[list[object], int | None]:
    """Expand a compact deterministic recipe into observation units."""
    recipe = case.get("recipe")
    if recipe == "literal":
        units = _unit_list(case.get("units"), "units")
        return units, case.get("loop_start")
    if recipe == "cycle":
        prefix = _unit_list(case.get("prefix", []), "prefix")
        prefix.extend(_range_units(case.get("prefix_range")))
        cycle = _nonempty_unit_list(case.get("cycle"), "cycle")
        repeats = _positive_int(case.get("repeats"), "repeats")
        suffix = _unit_list(case.get("suffix", []), "suffix")
        suffix.extend(_range_units(case.get("suffix_range")))
        return [*prefix, *(cycle * repeats), *suffix], len(prefix)
    if recipe == "indexed":
        prefix = _unit_list(case.get("prefix", []), "prefix")
        frame = _nonempty_unit_list(case.get("frame"), "frame")
        count = _positive_int(case.get("count"), "count")
        units = [*prefix]
        for index in range(count):
            units.extend(_format_unit(unit, index) for unit in frame)
        units.extend(_unit_list(case.get("suffix", []), "suffix"))
        return units, None
    if recipe == "perturbed_cycle":
        cycle = _nonempty_unit_list(case.get("cycle"), "cycle")
        repeats = _positive_int(case.get("repeats"), "repeats")
        perturb_every = _positive_int(case.get("perturb_every"), "perturb_every")
        units: list[object] = []
        for index in range(repeats):
            block = list(cycle)
            if (index + 1) % perturb_every == 0:
                block[-1] = f"variation-{index + 1}"
            units.extend(block)
        return units, None
    raise ValueError(f"{case.get('id', '<unknown>')}: unsupported recipe: {recipe}")


def evaluate(
    cases: Iterable[dict[str, Any]],
    *,
    detector_config: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Return content-free aggregate and per-class evaluation evidence."""
    configuration = detector_config or {
        "min_repeats": 8,
        "max_period": 16,
        "max_window": 512,
        "min_observed_units": 32,
    }
    rows: list[dict[str, Any]] = []
    for case in cases:
        units, loop_start = expand_case(case)
        guard = LoopSentry(**configuration)
        hit = guard.scan(units)
        flagged = hit is not None
        expected = case["expected"]
        matches = expected == "observe" or flagged == (expected == "flag")
        period_matches = (
            hit is None
            or case.get("expected_period") is None
            or hit.period == case["expected_period"]
        )
        latency = None
        if hit is not None and loop_start is not None:
            latency = hit.observed_units - loop_start
        rows.append(
            {
                "id": case["id"],
                "label": case["label"],
                "class": case["class"],
                "expected": expected,
                "flagged": flagged,
                "matches": matches and period_matches,
                "observed_units": guard.observed_units,
                "period": hit.period if hit is not None else None,
                "repeats": hit.repeats if hit is not None else None,
                "detection_latency_units": latency,
            }
        )

    pathological = [row for row in rows if row["label"] == "pathological"]
    benign = [row for row in rows if row["label"] == "benign"]
    ambiguous = [row for row in rows if row["label"] == "ambiguous"]
    latencies = sorted(
        row["detection_latency_units"]
        for row in pathological
        if row["detection_latency_units"] is not None
    )
    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"cases": 0, "flagged": 0, "mismatches": 0}
    )
    for row in rows:
        key = (row["label"], row["class"])
        grouped[key]["cases"] += 1
        grouped[key]["flagged"] += int(row["flagged"])
        grouped[key]["mismatches"] += int(not row["matches"])

    return {
        "schema_version": 1,
        "detector": "exact_periodic_loop",
        "detector_config": configuration,
        "totals": {
            "cases": len(rows),
            "pathological": len(pathological),
            "benign": len(benign),
            "ambiguous": len(ambiguous),
            "mismatches": sum(not row["matches"] for row in rows),
        },
        "rates": {
            "pathological_detection": _rate(pathological),
            "benign_false_positive": _rate(benign),
            "ambiguous_flagged": _rate(ambiguous),
        },
        "latency_units": _distribution(latencies),
        "classes": [
            {"label": label, "class": class_name, **statistics_row}
            for (label, class_name), statistics_row in sorted(grouped.items())
        ],
        "cases": rows,
    }


def benchmark(*, units: int = 50_000, observations: int = 5) -> dict[str, Any]:
    """Measure detector and null-loop cost without using timing as a CI gate."""
    if units < 1 or observations < 1:
        raise ValueError("benchmark units and observations must be positive")
    detector_samples: list[float] = []
    null_samples: list[float] = []
    sequence = tuple(range(997))

    for _ in range(observations):
        guard = LoopSentry()
        started = perf_counter_ns()
        for index in range(units):
            guard.push(sequence[index % len(sequence)])
        detector_samples.append((perf_counter_ns() - started) / units)

        started = perf_counter_ns()
        sink = 0
        for index in range(units):
            sink ^= sequence[index % len(sequence)]
        null_samples.append((perf_counter_ns() - started) / units)
        if sink == -1:  # pragma: no cover - keeps the loop observable to alternative runtimes
            raise AssertionError("unreachable")

    detector_median = statistics.median(detector_samples)
    null_median = statistics.median(null_samples)
    return {
        "units_per_observation": units,
        "observations": observations,
        "detector_ns_per_unit": _distribution(detector_samples),
        "null_ns_per_unit": _distribution(null_samples),
        "median_overhead_ratio": detector_median / null_median if null_median else None,
        "retained_units_after_run": guard.retained_units,
        "timing_is_ci_gate": False,
    }


def verify_manifest(corpus: Path, manifest_path: Path = MANIFEST) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest.get("corpora", {}).get(corpus.name)
    if entry is None:
        raise ValueError(f"{corpus.name} is not listed in {manifest_path}")
    digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
    if digest != entry.get("sha256"):
        raise ValueError(f"{corpus.name} SHA-256 does not match the manifest")
    cases = load_cases(corpus)
    if len(cases) != entry.get("cases"):
        raise ValueError(f"{corpus.name} case count does not match the manifest")
    counts = {label: sum(case["label"] == label for case in cases) for label in ALLOWED_LABELS}
    if counts != entry.get("labels"):
        raise ValueError(f"{corpus.name} label counts do not match the manifest")
    return {"sha256": digest, "cases": len(cases), "labels": counts}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--benchmark-units", type=int, default=50_000)
    parser.add_argument("--benchmark-observations", type=int, default=5)
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="return non-zero when a labelled expectation or period does not match",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = verify_manifest(args.corpus, args.manifest)
    report = evaluate(load_cases(args.corpus))
    report["corpus"] = {"name": args.corpus.name, **manifest}
    report["benchmark"] = benchmark(
        units=args.benchmark_units,
        observations=args.benchmark_observations,
    )

    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    _print_summary(report)
    return int(args.fail_on_mismatch and report["totals"]["mismatches"] > 0)


def _print_summary(report: dict[str, Any]) -> None:
    totals = report["totals"]
    rates = report["rates"]
    latency = report["latency_units"]
    timing = report["benchmark"]["detector_ns_per_unit"]
    print(f"LoopSentry corpus: {report['corpus']['name']} ({totals['cases']} cases)")
    print(f"Corpus SHA-256: {report['corpus']['sha256']}")
    print(
        "Pathological detection: "
        f"{rates['pathological_detection']:.1%}; "
        f"benign false positives: {rates['benign_false_positive']:.1%}; "
        f"ambiguous flagged: {rates['ambiguous_flagged']:.1%}"
    )
    print(
        "Detection latency in loop units: "
        f"median={latency['median']}, p95={latency['p95']}, max={latency['max']}"
    )
    print(
        "Detector timing (informational, not a CI gate): "
        f"median={timing['median']:.0f} ns/unit, p95={timing['p95']:.0f} ns/unit"
    )
    print(f"Expectation mismatches: {totals['mismatches']}")


def _unit_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be an array")
    for unit in value:
        try:
            hash(unit)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{field} units must be hashable JSON scalars") from error
    return list(value)


def _nonempty_unit_list(value: object, field: str) -> list[object]:
    units = _unit_list(value, field)
    if not units:
        raise ValueError(f"{field} must not be empty")
    return units


def _range_units(specification: object) -> list[str]:
    if specification is None:
        return []
    if not isinstance(specification, dict):
        raise TypeError("range specifications must be objects")
    prefix = specification.get("prefix")
    count = specification.get("count")
    if not isinstance(prefix, str):
        raise TypeError("range prefix must be a string")
    return [f"{prefix}-{index}" for index in range(_positive_int(count, "range count"))]


def _format_unit(unit: object, index: int) -> object:
    return unit.replace("{i}", str(index)) if isinstance(unit, str) else unit


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _rate(rows: list[dict[str, Any]]) -> float | None:
    if not rows:
        return None
    return sum(row["flagged"] for row in rows) / len(rows)


def _distribution(values: Sequence[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {"min": None, "median": None, "p95": None, "max": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, max(0, math.ceil(0.95 * len(ordered)) - 1))
    return {
        "min": ordered[0],
        "median": statistics.median(ordered),
        "p95": ordered[p95_index],
        "max": ordered[-1],
    }


if __name__ == "__main__":
    sys.exit(main())
