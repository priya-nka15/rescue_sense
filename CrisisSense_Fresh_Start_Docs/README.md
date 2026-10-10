# CrisisSense — Fresh-Start Documentation

**Status:** Planning baseline only. No implementation, dataset acquisition, model evaluation, or deployment is assumed complete.

CrisisSense is a proposed multimodal crisis-intelligence and event-context verification system that accepts **text, images, audio, and video**. It should help assess whether available evidence supports, contradicts, or is insufficient to verify claims about a crisis event. It must not present uncertainty as proof of falsity or claim that media is current without evidence.

## Start here
1. Read `AGENTS.md` and `CLAUDE.md`.
2. Read `PRD.md` and `OPEN_QUESTIONS.md`.
3. Complete Phase 0 in `TASKS.md` before installing packages, downloading datasets, or implementing models.
4. Record verified findings in `PROGRESS.md`; record consequential choices as ADRs.
5. Work on `main` unless the owner explicitly changes this rule. Never reset, discard, or overwrite user work without approval.

## Hardware and constraints
Current known local resources: Ubuntu, 8 GB RAM, CPU-only, about 12 GB free root storage (reported 2026-10-09). These are constraints to recheck, not assumptions that the whole disk is available. Start with lightweight baselines and inspect existing storage before installing large dependencies or downloading datasets/model weights.

## Important status rules
- This pack is a planning document, not evidence that code, datasets, checkpoints, or pipelines exist.
- The research gap and novelty are **unverified** until related work is reviewed.
- Dataset availability, labels, license, size, and suitability must be checked at official sources before use.
- Keep text, image, audio, and video in project scope, but do not promise every modality will be included in every experiment until suitable data and a valid evaluation design exist.
- Do not fabricate pairings between unrelated samples.
- Do not claim an experiment passed unless it was actually run and its output recorded.

## Documentation index
- Must-have: `AGENTS.md`, `CLAUDE.md`, `PRD.md`, `TASKS.md`, `PROGRESS.md`, `CODEBASE_MAP.md`
- Engineering: `CODING_STANDARDS.md`, `DATA_MODEL.md`, `ADRs/`, `ENVIRONMENT.md`, `SECURITY.md`
- Supporting: `GLOSSARY.md`, `UI_UX_SPEC.md`, `NON_FUNCTIONAL_REQUIREMENTS.md`, `CI_CD_RUNBOOK.md`, `OBSERVABILITY.md`, `OPEN_QUESTIONS.md`, `PROMPT_LIBRARY.md`

## First milestone
Complete a read-only feasibility audit and literature/data review. Do not begin model implementation until the research question, accessible data, labels, and evaluation design are agreed.
