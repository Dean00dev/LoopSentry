# Security policy

## Supported versions

LoopSentry is a research alpha. Security fixes are applied to the most recent tagged prerelease only.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** option on this repository's Security tab. Please include the affected version, a minimal reproduction, impact, and any suggested mitigation. Do not include private model output, provider credentials, or unrelated personal data.

If private vulnerability reporting is unavailable, contact the maintainer privately through the contact options on the maintainer's GitHub profile before publishing details.

## Security boundary

LoopSentry observes caller-supplied units and returns advisory evidence. It does not authenticate events, inspect model internals, cancel streams, or authorize tools. A clean LoopSentry result is not evidence that output is safe, correct, non-memorized, or policy-compliant. See [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md).
