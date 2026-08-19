"""Deterministic streaming evidence for repetitive generation.

LoopSentry v0.1 detects and reports. It does not terminate generation.
Enforcement is deliberately left to callers until evaluation supports a policy.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Hashable, Iterable

Token = Hashable


class Outcome(str, Enum):
    """Advisory control-flow outcome produced by the detector."""

    CONTINUE = "continue"
    FLAG = "flag"
    TERMINATE_ELIGIBLE = "terminate_eligible"


@dataclass(frozen=True)
class Detection:
    """Evidence for a detected repetitive pattern, not an enforcement command."""

    outcome: Outcome
    reason: str
    period: int
    repeats: int
    observed_units: int

    @property
    def observed_tokens(self) -> int:
        """Backward-compatible alias; units need not be model tokens."""
        return self.observed_units


class LoopSentry:
    """Incremental exact-cycle baseline over arbitrary hashable units.

    Callers may feed tokenizer IDs, words, characters, or another stable unit.
    Because units differ between integrations, cross-model latency claims must not
    average token counts without identifying the tokenizer/unit used.
    """

    def __init__(
        self,
        *,
        min_repeats: int = 8,
        max_period: int = 16,
        max_window: int = 512,
        min_observed_tokens: int = 32,
    ) -> None:
        if min_repeats < 2:
            raise ValueError("min_repeats must be >= 2")
        if max_period < 1:
            raise ValueError("max_period must be >= 1")
        if max_window < max_period * min_repeats:
            raise ValueError("max_window is too small for configured detection")
        if min_observed_tokens < 1:
            raise ValueError("min_observed_tokens must be >= 1")
        self.min_repeats = min_repeats
        self.max_period = max_period
        self.min_observed_tokens = min_observed_tokens
        self._window: deque[Token] = deque(maxlen=max_window)
        self._seen = 0

    @property
    def observed_tokens(self) -> int:
        return self._seen

    def push(self, token: Token) -> Detection | None:
        """Observe one unit and return evidence if an exact suffix cycle is detected."""
        self._window.append(token)
        self._seen += 1
        if self._seen < self.min_observed_tokens:
            return None

        data = list(self._window)
        for period in range(1, self.max_period + 1):
            need = period * self.min_repeats
            if len(data) < need:
                continue
            suffix = data[-need:]
            pattern = suffix[:period]
            if suffix == pattern * self.min_repeats:
                return Detection(
                    outcome=Outcome.FLAG,
                    reason="exact_periodic_loop",
                    period=period,
                    repeats=self.min_repeats,
                    observed_units=self._seen,
                )
        return None

    def scan(self, tokens: Iterable[Token]) -> Detection | None:
        """Feed units until the first detection; never terminates the source stream."""
        for token in tokens:
            detection = self.push(token)
            if detection is not None:
                return detection
        return None
