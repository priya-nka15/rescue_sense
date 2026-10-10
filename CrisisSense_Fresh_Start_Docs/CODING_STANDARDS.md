# Coding Standards / Style Guide

## General
- Use readable Python and small, focused functions.
- Prefer straightforward control flow over clever abstractions.
- Avoid unnecessary base classes, factories, plugin registries, and layers of wrappers.
- Type-hint public functions and structured API boundaries where it improves clarity.
- Use descriptive names; keep domain terms consistent with `GLOSSARY.md`.
- Explain non-obvious research choices, not obvious syntax.

## Python
- Follow PEP 8; use a formatter/linter only after selecting compatible tools.
- Use `pathlib` for paths.
- Keep randomness controlled and documented for experiments.
- Never fit preprocessing on validation/test data.
- Separate pure preprocessing from file/network operations where practical.
- Handle expected data/decoding errors explicitly; do not hide all exceptions with broad catches.
- Avoid loading full datasets into RAM if streaming/chunking is feasible.

## Research code
- Each experiment must identify dataset version, split manifest, model/checkpoint, preprocessing, parameters, seed, metrics, and output location.
- Do not mix synthetic data with real data without an explicit, separately reported experiment.
- Save predictions as well as aggregate metrics so results can be audited.
- Keep test-set use limited to final evaluation.
- Do not hard-code local absolute paths or tokens.

## API and schemas
- Use explicit request/response schemas.
- Distinguish invalid input, unsupported modality, processing failure, and insufficient evidence.
- Keep errors informative without leaking internal paths or secrets.
- Avoid silent API breaking changes.

## Tests
- Add focused unit tests for pure logic and schemas.
- Add integration tests for API and media validation.
- Include malformed input, missing modality, empty input, and size/duration boundary tests.
- Tests must not require downloading large models unless specifically marked as an optional integration suite.

## Git hygiene
- Small, descriptive commits after owner approval.
- Never commit data, model checkpoints, caches, logs, secrets, `.env`, virtual environments, or generated media.
