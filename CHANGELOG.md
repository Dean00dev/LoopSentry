# Changelog

All notable changes are documented here. LoopSentry uses semantic versioning, including prerelease identifiers while the public API is experimental.

## [Unreleased]

Nothing yet.

## [0.2.0-alpha.1] - 2026-08-20

### Added

- Separate `FLAG` and `TERMINATE_ELIGIBLE` outcomes so detection does not silently become enforcement.
- Content-free JSON receipts with observed span, actual retained repeat count, and bounded-window disclosure.
- Optional event normalizer for model-provider, agent, and tool streams.
- Reusable detector state through `reset()`.
- Standard-library `loopsentry scan` CLI for characters, words, lines, and canonical JSONL.
- Tamper-bound 32-case synthetic corpus split into pathological, benign, and ambiguous classes.
- Machine-readable evaluation reports and non-gating performance observations.
- Typed-package marker and Python 3.10–3.14 metadata.
- Apache-2.0 license text, NOTICE, security policy, contribution guide, threat model, integration guide, and verification receipt.
- Hosted CI across Linux, macOS, and Windows, plus distribution build and clean-environment smoke tests.

### Changed

- Report the longest observed repeat run retained in the bounded window instead of merely echoing the configured threshold.
- Rename the primary observation language from “tokens” to provider-neutral “units”; the v0.1 token properties remain as compatibility aliases.
- Pin third-party CI actions to full commit SHAs.
- Describe timing as environment-specific evidence rather than a release gate.

### Fixed

- Resolve the three Ruff failures that made every hosted v0.1 CI job red before tests executed.
- Reject invalid boolean and non-integer thresholds consistently.
- Reject unhashable normalized units without partially advancing detector state.

[Unreleased]: https://github.com/Dean00dev/LoopSentry/compare/v0.2.0-alpha.1...HEAD
[0.2.0-alpha.1]: https://github.com/Dean00dev/LoopSentry/compare/v0.1.0-alpha.1...v0.2.0-alpha.1
