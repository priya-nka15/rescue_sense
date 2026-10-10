# ADR-0001: Keep Four Modalities in Project Scope

- **Status:** Accepted as a scope requirement; feasibility remains to be demonstrated.
- **Date:** 2026-10-09

## Context
The project owner explicitly requires text, image, audio, and video inputs. The local machine is reported as Ubuntu with 8 GB RAM, CPU-only, and approximately 12 GB free root storage.

## Decision
Retain all four modalities in the intended product scope. Develop incrementally and evaluate each modality only when suitable data, labels, model feasibility, and an evaluation protocol are established. Do not promise all four will appear in every research experiment.

## Alternatives considered
- Restrict project to text-image only.
- Implement all four modalities simultaneously.
- Keep all four in scope but stage implementation.

## Consequences
- Staged work and strict acceptance gates are required.
- Audio transcription is not the same task as environmental sound classification.
- Video frame analysis alone does not establish temporal understanding; sampled frames are derived from video.
- Multimodal claims require authentic, documented sample/event relationships.
- Scope may need to be narrowed for the core paper if suitable linked data is unavailable; any such change must be discussed with the owner.
