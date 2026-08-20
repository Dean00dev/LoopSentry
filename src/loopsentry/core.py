"""Bounded, deterministic evidence for exact repetitive generation.

LoopSentry observes equality-stable units. It reports exact suffix cycles and
never terminates a source stream itself. Callers own the enforcement policy.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeAlias

Unit: TypeAlias = Any
Key: TypeAlias = Hashable
KeyFunction: TypeAlias = Callable[[Unit], Key]


class Outcome(str, Enum):
    """Advisory control-flow outcome produced by the detector."""

    CONTINUE = "continue"
    FLAG = "flag"
    TERMINATE_ELIGIBLE = "terminate_eligible"


@dataclass(frozen=True, slots=True)
class Detection:
    """Content-free evidence for an exact periodic suffix.

    ``start_unit`` is zero-based and inclusive. ``end_unit`` is exclusive.
    ``repeats`` is the number of complete periods retained as evidence, not
    merely the configured threshold. When ``window_limited`` is true, that
    repeat count is a lower bound because the cycle reaches beyond the bounded
    observation window.
    """

    outcome: Outcome
    reason: str
    period: int
    repeats: int
    observed_units: int
    matched_units: int
    start_unit: int
    end_unit: int
    window_limited: bool

    @property
    def observed_tokens(self) -> int:
        """Backward-compatible alias; observed units need not be model tokens."""
        return self.observed_units

    def as_dict(self) -> dict[str, bool | int | str]:
        """Return a JSON-safe receipt that never includes observed content."""
        return {
            "outcome": self.outcome.value,
            "reason": self.reason,
            "period": self.period,
            "repeats": self.repeats,
            "observed_units": self.observed_units,
            "matched_units": self.matched_units,
            "start_unit": self.start_unit,
            "end_unit": self.end_unit,
            "window_limited": self.window_limited,
        }


class LoopSentry:
    """Incremental exact-cycle detector over normalized, hashable units.

    Feed tokenizer IDs, words, characters, tool-event keys, or another stable
    unit. A ``key`` function can reduce mutable provider events to a hashable,
    privacy-preserving representation before they enter bounded state.

    Detection and termination are separate thresholds. ``min_repeats`` emits
    :class:`Outcome.FLAG`. If ``terminate_repeats`` is configured, a continuing
    cycle becomes :class:`Outcome.TERMINATE_ELIGIBLE` at that larger threshold.
    The detector never cancels or closes the source stream itself.
    """

    def __init__(
        self,
        *,
        min_repeats: int = 8,
        terminate_repeats: int | None = None,
        max_period: int = 16,
        max_window: int = 512,
        min_observed_units: int | None = None,
        min_observed_tokens: int | None = None,
        key: KeyFunction | None = None,
    ) -> None:
        self.min_repeats = _bounded_int("min_repeats", min_repeats, minimum=2)
        self.max_period = _bounded_int("max_period", max_period, minimum=1)
        self.max_window = _bounded_int("max_window", max_window, minimum=1)

        if min_observed_units is not None and min_observed_tokens is not None:
            raise ValueError(
                "set min_observed_units or the legacy min_observed_tokens alias, not both"
            )
        observed_threshold = (
            min_observed_units
            if min_observed_units is not None
            else min_observed_tokens
            if min_observed_tokens is not None
            else 32
        )
        self.min_observed_units = _bounded_int("min_observed_units", observed_threshold, minimum=1)

        if terminate_repeats is not None:
            terminate_repeats = _bounded_int(
                "terminate_repeats", terminate_repeats, minimum=self.min_repeats
            )
        self.terminate_repeats = terminate_repeats

        evidence_repeats = terminate_repeats or self.min_repeats
        required_window = self.max_period * evidence_repeats
        if self.max_window < required_window:
            raise ValueError(
                "max_window is too small to retain the configured maximum-period evidence "
                f"({required_window} units required)"
            )
        if key is not None and not callable(key):
            raise TypeError("key must be callable")
        self._key = key
        self._window: deque[Key] = deque(maxlen=self.max_window)
        self._seen = 0
        self._last_detection: Detection | None = None

    @property
    def observed_units(self) -> int:
        """Total accepted units observed since construction or the last reset."""
        return self._seen

    @property
    def min_observed_tokens(self) -> int:
        """Backward-compatible alias for the configured observation threshold."""
        return self.min_observed_units

    @property
    def observed_tokens(self) -> int:
        """Backward-compatible alias; observed units need not be model tokens."""
        return self._seen

    @property
    def retained_units(self) -> int:
        """Number of normalized units currently retained in bounded state."""
        return len(self._window)

    @property
    def last_detection(self) -> Detection | None:
        """Most recent detection, or ``None`` after a clear unit or reset."""
        return self._last_detection

    def reset(self) -> None:
        """Clear all stream state while preserving configuration."""
        self._window.clear()
        self._seen = 0
        self._last_detection = None

    def push(self, unit: Unit) -> Detection | None:
        """Observe one unit and return evidence for an exact suffix cycle."""
        normalized = self._normalize(unit)
        self._window.append(normalized)
        self._seen += 1

        if self._seen < self.min_observed_units:
            self._last_detection = None
            return None

        detection = self._detect(tuple(self._window))
        self._last_detection = detection
        return detection

    def scan(
        self,
        units: Iterable[Unit],
        *,
        minimum_outcome: Outcome = Outcome.FLAG,
    ) -> Detection | None:
        """Feed units until the requested outcome is reached.

        The default preserves v0.1 behaviour by returning the first flag. Ask
        for ``TERMINATE_ELIGIBLE`` to continue through advisory flags until the
        configured escalation threshold is observed.
        """
        try:
            minimum_outcome = Outcome(minimum_outcome)
        except ValueError as error:
            raise ValueError("minimum_outcome must be flag or terminate_eligible") from error
        if minimum_outcome is Outcome.CONTINUE:
            raise ValueError("minimum_outcome must be flag or terminate_eligible")
        if minimum_outcome is Outcome.TERMINATE_ELIGIBLE and self.terminate_repeats is None:
            raise ValueError(
                "terminate_repeats must be configured before waiting for terminate_eligible"
            )

        for unit in units:
            detection = self.push(unit)
            if detection is None:
                continue
            if minimum_outcome is Outcome.FLAG or detection.outcome is minimum_outcome:
                return detection
        return None

    def _normalize(self, unit: Unit) -> Key:
        normalized = self._key(unit) if self._key is not None else unit
        try:
            hash(normalized)
        except (TypeError, ValueError) as error:
            raise TypeError("observed units must be hashable after key normalization") from error
        return normalized

    def _detect(self, data: tuple[Key, ...]) -> Detection | None:
        largest_period = min(self.max_period, len(data) // self.min_repeats)
        for period in range(1, largest_period + 1):
            pattern = data[-period:]
            repeats = 1
            cursor = len(data) - (2 * period)
            while cursor >= 0 and data[cursor : cursor + period] == pattern:
                repeats += 1
                cursor -= period
            if repeats < self.min_repeats:
                continue

            matched_units = repeats * period
            outcome = (
                Outcome.TERMINATE_ELIGIBLE
                if self.terminate_repeats is not None and repeats >= self.terminate_repeats
                else Outcome.FLAG
            )
            return Detection(
                outcome=outcome,
                reason="exact_periodic_loop",
                period=period,
                repeats=repeats,
                observed_units=self._seen,
                matched_units=matched_units,
                start_unit=self._seen - matched_units,
                end_unit=self._seen,
                window_limited=matched_units == len(data) and self._seen > len(data),
            )
        return None


def _bounded_int(name: str, value: object, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value
