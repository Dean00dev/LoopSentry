"""Standard-library command line interface for LoopSentry."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Iterator, Sequence
from contextlib import nullcontext
from pathlib import Path
from typing import TextIO

from . import __version__
from .core import LoopSentry, Outcome

EXIT_CLEAR = 0
EXIT_FLAG = 10
EXIT_TERMINATE_ELIGIBLE = 20


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loopsentry",
        description="Detect exact periodic loops without retaining or printing source content.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan a text or JSONL stream")
    scan.add_argument("source", nargs="?", default="-", help="input path; '-' reads stdin")
    scan.add_argument(
        "--unit",
        choices=("characters", "words", "lines", "jsonl"),
        default="words",
        help="observation unit (default: words)",
    )
    scan.add_argument("--min-repeats", type=int, default=8)
    scan.add_argument("--terminate-repeats", type=int)
    scan.add_argument("--max-period", type=int, default=16)
    scan.add_argument("--max-window", type=int, default=512)
    scan.add_argument("--min-observed-units", type=int, default=32)
    scan.add_argument(
        "--stop-on",
        choices=("flag", "terminate_eligible"),
        default="flag",
        help="minimum outcome returned by the scan",
    )
    scan.add_argument(
        "--pretty",
        action="store_true",
        help="indent the content-free JSON receipt",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "scan":
        parser.error("a command is required")

    try:
        guard = LoopSentry(
            min_repeats=args.min_repeats,
            terminate_repeats=args.terminate_repeats,
            max_period=args.max_period,
            max_window=args.max_window,
            min_observed_units=args.min_observed_units,
        )
        minimum_outcome = Outcome(args.stop_on)
        with _open_source(args.source) as handle:
            detection = guard.scan(
                iter_units(handle, args.unit),
                minimum_outcome=minimum_outcome,
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    receipt: dict[str, object] = {
        "schema_version": 1,
        "detected": detection is not None,
        "observed_units": guard.observed_units,
        "retained_units": guard.retained_units,
        "detection": detection.as_dict() if detection is not None else None,
    }
    json.dump(receipt, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")

    if detection is None:
        return EXIT_CLEAR
    if detection.outcome is Outcome.TERMINATE_ELIGIBLE:
        return EXIT_TERMINATE_ELIGIBLE
    return EXIT_FLAG


def iter_units(handle: TextIO, mode: str) -> Iterator[object]:
    """Yield normalized units from a text stream without retaining the input."""
    if mode == "characters":
        while chunk := handle.read(8192):
            yield from chunk
        return
    if mode == "words":
        for line in handle:
            yield from re.findall(r"\S+", line)
        return
    if mode == "lines":
        for line in handle:
            yield line.rstrip("\r\n")
        return
    if mode == "jsonl":
        yield from _jsonl_units(handle)
        return
    raise ValueError(f"unsupported unit mode: {mode}")


def _jsonl_units(lines: Iterable[str]) -> Iterator[str]:
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise json.JSONDecodeError(
                f"line {line_number}: {error.msg}",
                error.doc,
                error.pos,
            ) from error
        yield json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _open_source(source: str):
    if source == "-":
        return nullcontext(sys.stdin)
    return Path(source).open(encoding="utf-8")
