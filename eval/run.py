"""Run the versioned LoopSentry corpus against the exact-periodicity baseline."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter_ns

from loopsentry import LoopSentry

CORPUS = Path(__file__).parent / "corpus" / "v0.1.0.jsonl"


def load_cases():
    with CORPUS.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def main() -> None:
    rows = []
    for case in load_cases():
        guard = LoopSentry()
        start = perf_counter_ns()
        hit = guard.scan(case["units"])
        elapsed_ns = perf_counter_ns() - start
        rows.append({**case, "flagged": hit is not None, "elapsed_ns": elapsed_ns})

    grouped = defaultdict(lambda: {"n": 0, "flagged": 0})
    for row in rows:
        key = (row["label"], row["class"])
        grouped[key]["n"] += 1
        grouped[key]["flagged"] += int(row["flagged"])

    print("LoopSentry corpus:", CORPUS.name)
    print("Per-class results (aggregate-only reporting is intentionally insufficient):")
    for (label, cls), stats in sorted(grouped.items()):
        rate = stats["flagged"] / stats["n"]
        print(f"{label:12} {cls:30} n={stats['n']:3d} flagged={rate:.1%}")

    timings = sorted(row["elapsed_ns"] for row in rows)
    if timings:
        p99_index = min(len(timings) - 1, int(0.99 * len(timings)))
        print(f"p99 detector wall time (tiny corpus; not a performance claim): {timings[p99_index]} ns")


if __name__ == "__main__":
    main()
