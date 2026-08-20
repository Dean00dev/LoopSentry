# Verification receipt — v0.2.0-alpha.1

**Prepared:** 2026-08-20  
**Release status:** prerelease candidate  
**Scope:** repository source, deterministic corpus, Python package, CLI, and CI definition

This receipt separates reproduced evidence from pending hosted evidence. It should be amended with the exact commit and workflow URL after the release candidate passes on GitHub-hosted runners.

## Reproduced locally

| Check | Result |
|---|---|
| Ruff lint | Pass |
| Ruff format check | Pass |
| Python compilation | Pass |
| Pytest suite | 40 tests plus 9 subtests pass |
| Standard-library unittest suite | Pass |
| Wheel and source distribution build | Pass |
| Clean-environment wheel install and CLI smoke | Pass |
| Manifest-bound evaluator | 32 cases, 0 expectation mismatches |
| Pathological synthetic fixtures | 12/12 detected |
| Benign synthetic fixtures | 0/16 flagged |
| Ambiguous synthetic fixtures | 4/4 flagged, reported separately |
| Corpus SHA-256 | `832b49076ecb3469e0b3d539396e463edcdb89cdd3ae867488d1661af44835bf` |
| Retained runtime state | Bounded by configured `max_window` |
| Runtime dependencies | None declared |

The locally built wheel contains the five package files, metadata, entry point, complete license, and NOTICE. It declares no runtime dependency. Artifact hashes are not embedded here because this receipt itself is included in the source distribution; claiming that archive's hash inside itself would be self-referential rather than reproducible evidence.

Exact commands:

```bash
ruff check .
ruff format --check .
python -m compileall -q src eval tests
pytest
python -m unittest discover -s tests -v
python eval/run.py --json-output reports/evaluation-v0.2.0.json --fail-on-mismatch
python -m build
```

Timing output is intentionally omitted from the release claim because it varies by environment and is not a CI gate.

## Hosted evidence

Pending first run of this release candidate. The workflow is configured for:

- quality and corpus evaluation on Ubuntu with Python 3.14;
- package tests on Ubuntu 3.10/3.11/3.12/3.13/3.14;
- package tests on macOS 3.10/3.14;
- package tests on Windows 3.10/3.14;
- wheel and source-distribution build after all gates;
- clean-environment wheel installation and CLI smoke test;
- uploaded evaluation and distribution artifacts.

## Disclosed prior failure

The previous `main` commit's hosted [CI run #5](https://github.com/Dean00dev/LoopSentry/actions/runs/32233775100) failed on all nine matrix jobs. Installation succeeded, then Ruff stopped the workflow on three source/test style findings before tests executed. v0.2 fixes those findings and restructures CI so quality, evaluation, tests, and packaging have explicit receipts. The historical failure is not represented as passing evidence.

## Not demonstrated by this receipt

- real-world detection or false-positive rates;
- semantic-loop detection;
- suitability of default thresholds for a production application;
- provider cancellation or agent containment;
- Python implementations other than CPython on the named hosted images;
- security against an adversary who controls event normalization;
- artifact publication to a package index;
- stable API compatibility beyond the documented v0.1 aliases.
