# Evaluation protocol

LoopSentry's evaluation is designed to make a small synthetic result reproducible without disguising it as a real-world rate.

## Versioned corpus

`eval/corpus/v0.2.0.jsonl` contains 32 deterministic recipes:

| Label | Cases | Treatment |
|---|---:|---|
| Pathological | 12 | Expected to flag |
| Benign | 16 | Expected to remain clear |
| Ambiguous | 4 | Observed and reported; never counted as success or false positive |

The manifest binds the filename, exact byte-level SHA-256, case count, and label counts. The evaluator rejects a changed corpus until the manifest is deliberately updated. Repository attributes force corpus checkout to LF on every supported operating system so the byte-level identity is cross-platform.

Current corpus SHA-256:

```text
832b49076ecb3469e0b3d539396e463edcdb89cdd3ae867488d1661af44835bf
```

## Committed-alpha result

At the evaluator's committed configuration (`min_repeats=8`, `max_period=16`, `max_window=512`, `min_observed_units=32`):

- pathological detection: 12/12;
- benign false positives: 0/16;
- ambiguous flagged: 4/4, disclosed separately;
- pathological detection latency: 32 units median, 128 units p95 and maximum;
- expectation mismatches: 0.

This says exactly how one detector behaves on one small synthetic corpus. It does not estimate behaviour on natural conversations, production agents, arbitrary tokenizers, or adversarially chosen inputs.

## Reproduction

```bash
python -m pip install -e ".[dev]"
python eval/run.py \
  --json-output reports/evaluation-v0.2.0.json \
  --benchmark-units 50000 \
  --benchmark-observations 5 \
  --fail-on-mismatch
```

The JSON report contains detector configuration, aggregate rates, per-class counts, content-free per-case outcomes, detection latency, corpus identity, and benchmark observations.

## Timing policy

The benchmark compares detector-loop time with a simple null loop and records bounded state after the run. It is environment-sensitive and deliberately does not fail CI. Hardware, Python build, load, normalized key type, period bounds, and window size all affect timing. A release may report the exact hosted artifact; it must not turn one runner's number into a general performance guarantee.

## Adding evidence

New detector behaviour needs all three kinds of fixture:

1. pathological cases the behaviour is intended to catch;
2. benign cases that resemble the target but should remain clear;
3. ambiguous cases where the correct policy depends on application intent.

The cheapest way to improve a rate is to relabel difficult cases. Review should therefore treat corpus diffs as product-code diffs and require an explanation for every expectation change.
