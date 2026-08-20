# Threat model

## Asset and purpose

LoopSentry aims to provide bounded, deterministic evidence that an observed stream ends in an exact periodic cycle. The protected operational asset is primarily wasted time or compute from a stuck generation or agent loop. It is not designed to protect model weights or prove output safety.

## Trust boundaries

- **Caller:** chooses observation units, normalization, configuration, and enforcement.
- **Observed source:** may be buggy, adversarial, or simply repetitive by design.
- **LoopSentry:** compares normalized equality keys and emits local evidence.
- **Policy layer:** interprets a receipt and owns any external side effect.
- **Logs/artifacts:** may store receipts but should not receive source content from LoopSentry.

## In-scope failure modes

- unbounded detector memory;
- a finding that contains observed source values;
- malformed configuration that creates an unreachable threshold;
- partial state mutation when a unit is rejected;
- unstable period selection for the same unit sequence and configuration;
- confusing an advisory observation with automatic termination.

## Expected evasions and ambiguities

- A semantic loop can vary wording or event identifiers and never repeat exact keys.
- An adversary controlling normalization can add changing noise to evade equality.
- An over-broad normalizer can make useful work appear identical.
- Legitimate output can be exactly repetitive, including generated data, music, tables, logs, tests, and user-requested repetition.
- A bounded window cannot prove when a long cycle began before retained state.
- A forged receipt can be constructed by code outside LoopSentry; receipts are not signed attestations.

## Out of scope

- memorization and training-data provenance;
- prompt injection, jailbreak detection, or content moderation;
- semantic progress and answer correctness;
- provider authentication and transport integrity;
- tool authorization and sandboxing;
- availability of the process hosting LoopSentry.

## Mitigations

- hard state bounds and validated configuration;
- content-free receipt schema;
- separate flag and termination-eligible thresholds;
- caller-owned enforcement;
- labelled pathological, benign, and ambiguous fixtures;
- reproducible manifest-bound evaluation;
- CI across supported Python versions and operating systems.

These mitigations reduce specific implementation and reporting risks. They do not convert LoopSentry into a general AI safety mechanism.
