# ADR-0002: Local, Resource-Constrained Development

- **Status:** Accepted provisionally.
- **Date:** 2026-10-09

## Context
The owner decided to work on their own Ubuntu system. Reported capacity: 8 GB RAM, CPU-only, about 12 GB free root storage.

## Decision
Start with lightweight baselines and minimal dependencies. Inspect free storage before installs/downloads. Prefer pretrained inference and small classical models. Do not require a GPU or paid API for the core workflow unless feasibility review proves it necessary and the owner approves.

## Consequences
- Large model weights and datasets need an explicit size/access review.
- Process one sample or small batches for media experiments.
- Consider remote resources only if the owner later approves them.
- Recheck machine resources; figures may change.
