# Non-Functional Requirements

Numeric targets must be established after a minimal baseline and hardware tests. Do not invent performance targets in advance.

## Reproducibility
- Data versions, split manifests, model revisions, preprocessing, seeds, and commands recorded.
- Metrics trace to saved predictions.
- Fresh setup instructions tested.

## Resource use
- Support a CPU-first development path.
- Bound memory, file size, duration, resolution, and number of sampled video frames.
- Process media incrementally where feasible.
- Measure runtime, peak memory, and disk use for representative inputs.
- Do not download large weights/data without approval.

## Reliability
- Gracefully handle malformed, unsupported, missing, or corrupt modalities.
- One modality failing should not fabricate evidence from another.
- Distinguish processing failure from insufficient evidence.
- Tests cover expected failures.

## Research validity
- Evaluation split strategy matches the research question.
- Avoid duplicate and event leakage.
- Report per-class performance and error analysis.
- Report limitations, class imbalance, and dataset shift.
- Confidence calibration is claimed only when measured.

## Security and privacy
- Apply upload limits and safe decoding.
- Do not log raw media or sensitive metadata by default.
- Keep secrets out of source control.
- External data transfer requires explicit approval and disclosure.

## Maintainability
- Small modules, focused functions, clear schema, and useful tests.
- Avoid unnecessary architecture.
- Keep documentation aligned with the actual implementation.
