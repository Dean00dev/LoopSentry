# Integration patterns

LoopSentry works at the boundary where your application can observe a stream. It does not require model weights, logits, or a particular inference framework.

## Model-token streams

Tokenizer IDs are efficient equality keys when your stack exposes them:

```python
guard = LoopSentry(min_repeats=4, terminate_repeats=8)

for token_id, text_delta in provider_stream:
    finding = guard.push(token_id)
    yield text_delta
    if finding and finding.outcome is Outcome.TERMINATE_ELIGIBLE:
        await policy.review_or_cancel(finding.as_dict())
```

Do not assume token thresholds transfer between tokenizers. Record the tokenizer and detector configuration beside any evaluation result.

## Hosted text streams

When a provider exposes only text deltas, decide whether characters, words, or accumulated tokenizer output represent progress. Chunk boundaries are transport details and usually make poor units: two providers may split identical text differently.

The CLI can scan recorded text by characters, words, or lines. For live integration, normalize provider chunks before calling `push()`.

## Agent and tool streams

Exact repeated events can indicate a retry loop even when natural-language output changes. Normalize events to fields that represent control-flow progress:

```python
def progress_key(event):
    return (
        event["kind"],
        event.get("tool_name"),
        event.get("state"),
        event.get("error_code"),
    )


guard = LoopSentry(
    min_repeats=3,
    terminate_repeats=6,
    max_period=4,
    max_window=64,
    min_observed_units=6,
    key=progress_key,
)
```

Do not include credentials or full prompts in the key. Conversely, a key that discards every argument may collapse separate legitimate calls into one apparent loop. Test the normalizer against your own benign traces.

## Engine-native controls

Use engine-native controls when they fit the deployment. [vLLM exposes repeated n-gram termination parameters](https://docs.vllm.ai/en/latest/api/vllm/sampling_params/), and [Transformers supports repetition processors and custom stopping criteria](https://huggingface.co/docs/transformers/main_classes/text_generation). LoopSentry is useful when observation happens outside the engine, when streams contain non-token events, or when a content-free receipt and external policy split are valuable.

## Enforcement checklist

Before acting automatically on `TERMINATE_ELIGIBLE`:

- evaluate thresholds on representative, authorized traces;
- decide whether a warning, retry, fallback model, human review, or cancellation is appropriate;
- preserve the content-free receipt and exact detector configuration;
- bound retries so LoopSentry does not become one component in a larger loop;
- expose a user-visible explanation when cancellation affects them;
- monitor ambiguous and false-positive cases after deployment.
