# ADR-0003: Validate Research Gap Before Model Selection

- **Status:** Accepted.
- **Date:** 2026-10-09

## Context
Multimodal crisis classification and text-image relationship modelling already have prior work. Novelty cannot be assumed from combining modalities or pretrained models.

## Decision
Complete a related-work comparison and dataset feasibility assessment before committing to the research method. The primary contribution is a hypothesis until experimentally and bibliographically justified.

## Consequences
- No novelty claims in README, abstract, or proposal before review.
- Dataset choice must match the target label and evaluation question.
- If the original idea overlaps closely with prior work, revise the question rather than disguising the overlap.
