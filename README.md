# LoopSentry

**Stop pathological loops without pretending to solve memorization.**

LoopSentry is a model-agnostic runtime guard for detecting and terminating pathological repetitive generation, with a reproducible evaluation suite for measuring false positives, detection latency, and overhead.

> **Status:** early research alpha. The API and thresholds will change as the evaluation corpus grows.

## Why

Generative models can enter repetitive or cyclic output states. Besides producing bad responses, runaway generation can waste tokens and compute. Repetitive generation has also appeared in historical research on training-data divergence. LoopSentry addresses the observable runtime failure class: it does **not** claim to remove memorized information or prevent every extraction technique.

## Design principles

- **Model agnostic:** feed token IDs, words, characters, or other stable units.
- **Streaming:** inspect output incrementally rather than after generation finishes.
- **Deterministic evidence:** stops have an explicit reason, period, repeat count, and detection point.
- **Bounded state:** memory use does not grow with the response forever.
- **False positives matter:** legitimate bounded repetition must be represented in evaluation.
- **Claims follow tests:** security and performance claims are not made until reproduced by the public benchmark.

## Quickstart

```python
from loopsentry import LoopSentry

guard = LoopSentry()

for token in model_stream:
    detection = guard.push(token)
    if detection:
        cancel_generation()
        print(detection)
        break
```

The initial detector catches exact periodic suffix loops. More subtle degeneration belongs in later detector modules only after adversarial and benign fixtures exist for them.

## Scope for v0.1

LoopSentry aims to detect exact token repetition and short periodic cycles during streaming generation; produce machine-readable termination evidence; maintain bounded runtime state; and ship a reproducible benchmark covering pathological and benign repetitive workloads.

### Explicit non-claims

LoopSentry does **not** claim to:

- remove memorized training data from model weights;
- prevent all training-data extraction;
- identify whether arbitrary generated text came from training data;
- detect every possible generation pathology;
- make a model safe merely because no loop was detected.

## Evaluation contract

Before a stable v0.1 release, the repository should report at least:

- pathological-case detection rate;
- benign false-positive rate;
- tokens-to-detection distribution;
- runtime overhead;
- memory overhead;
- results by detector and fixture category.

The benchmark corpus should include both obvious attacks and legitimate repetition such as bounded lists, code, tables, logs, structured sequences, and repeated user-requested text.

## Security research ethics

LoopSentry's extraction-related fixtures should use synthetic canaries or controlled local/open models. Do not use this project to probe production services for private training data or to collect leaked personal information.

## License

Apache-2.0.
