# Contributing to LoopSentry

LoopSentry welcomes small, evidence-backed contributions. The detector is intentionally narrow; a new heuristic should not land without adversarial, benign, and ambiguous fixtures that make its trade-off inspectable.

## Before opening a change

1. For a behaviour change, open an issue describing the observable failure and the proposed evidence.
2. Do not submit private, leaked, or questionably sourced model output. Use synthetic fixtures or output you are authorized to publish.
3. Keep detection separate from enforcement. Core code must never close a provider stream or execute a tool.
4. Do not add runtime dependencies without explaining why the standard library is insufficient.

## Local checks

Use Python 3.10 or newer:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
python -m unittest discover -s tests -v
python eval/run.py --fail-on-mismatch
python -m build
```

Windows PowerShell activation is `.venv\Scripts\Activate.ps1`; the remaining commands are unchanged.

## Corpus changes

- Give every fixture a stable, unique ID.
- Label it `pathological`, `benign`, or `ambiguous` and explain the class in the pull request.
- Do not turn ambiguous cases into labelled victories to improve a headline rate.
- Update `eval/corpus/MANIFEST.json` with the exact case count, label counts, and SHA-256.
- Explain any changed metric in the changelog.

## Pull requests

Keep commits focused. Include tests for the defect or contract being changed, state what you ran, and distinguish local evidence from hosted-run evidence. By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
