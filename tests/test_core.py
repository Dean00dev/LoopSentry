import pytest

from loopsentry import LoopSentry


def test_detects_single_token_loop():
    guard = LoopSentry(min_repeats=8, min_observed_tokens=8)
    hit = guard.scan(["poem"] * 100)
    assert hit is not None
    assert hit.period == 1
    assert hit.reason == "exact_periodic_loop"


def test_detects_multi_token_cycle():
    guard = LoopSentry(min_repeats=6, max_period=4, min_observed_tokens=12)
    hit = guard.scan((["A", "B"] * 20))
    assert hit is not None
    assert hit.period == 2


def test_does_not_stop_short_bounded_repetition_by_default():
    guard = LoopSentry()
    assert guard.scan(["hello"] * 20) is None


def test_does_not_stop_nonperiodic_text():
    guard = LoopSentry(min_observed_tokens=8)
    tokens = "the quick brown fox jumps over the lazy dog then leaves quietly".split()
    assert guard.scan(tokens) is None


def test_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        LoopSentry(min_repeats=1)
