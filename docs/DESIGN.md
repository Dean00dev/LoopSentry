# Design and invariants

LoopSentry v0.2 has one deliberately narrow detector: exact periodic suffix repetition over equality-stable units.

## Processing boundary

For each accepted unit:

1. The optional `key` function converts the caller's object into a hashable value.
2. That value enters a `deque` bounded by `max_window`.
3. Once `min_observed_units` is reached, periods from `1` through `max_period` are tested against the current suffix.
4. The shortest period with at least `min_repeats` complete retained repeats produces a receipt.
5. The outcome is `flag` until the independently configured `terminate_repeats` threshold is reached.

The detector does not own the source stream and cannot cancel it. A caller may ignore, record, throttle, request human review, or terminate based on its own policy.

## Public invariants

- `max_window` bounds retained normalized units.
- A normalized unit must be hashable; rejection occurs before counters or retained state change.
- `max_window` must be large enough to retain the maximum configured period at the enforcement threshold.
- `start_unit` is zero-based and inclusive; `end_unit` is exclusive.
- `repeats` is the complete repeat count visible in retained evidence, not the configured minimum.
- `window_limited: true` means the reported run may have started before retained evidence.
- Receipts contain counts and coordinates, never the observed unit values.
- `reset()` clears all per-stream state while preserving configuration.

## Bounds

Let `W = max_window` and `P = max_period`.

- retained memory is `O(W)` normalized units;
- the exact-cycle search is bounded by `O(P × W)` equality work per accepted unit in the worst case;
- neither bound grows with the total lifetime of the stream.

These are algorithmic bounds, not latency guarantees. Equality cost is controlled by the caller's normalized key type; expensive custom equality can dominate detector work.

## Why shortest period wins

`x x x x` can be described as a period-one loop or a period-two loop. Returning the shortest matching period provides the fundamental explanation and makes receipts stable across a larger `max_period` setting.

## Why outcomes are staged

A single threshold made the v0.1 example look as though any detection should immediately cancel generation. That collapsed observation and policy. v0.2 can emit an earlier `FLAG` while requiring a longer continuing cycle before `TERMINATE_ELIGIBLE`. Even then, eligibility is advice; the application remains responsible for consequences.

## Privacy boundary

The receipt is content-free, but the detector must retain normalized values temporarily to compare them. A `key` function can reduce a rich event to a compact tuple, yet that function is user policy rather than a sanitizer supplied by LoopSentry. Avoid retaining secrets in normalized keys.
