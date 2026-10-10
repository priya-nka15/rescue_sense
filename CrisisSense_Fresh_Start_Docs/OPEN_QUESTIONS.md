# Known Issues / Open Questions / Assumptions

## Known status
- Project implementation starts from zero by user instruction.
- No datasets, checkpoints, experiments, API, UI, or deployment are considered complete.
- Local environment reported: Ubuntu, 8 GB RAM, CPU-only, around 12 GB free root storage. Recheck before action.
- Text, image, audio, and video are required project modalities.
- The project must be built locally unless the owner changes this decision.

## Research questions to resolve
1. What exact claim will the core method verify: incident identity, location/time consistency, recycled-media detection, or a carefully defined subset?
2. Which closest prior works already address the proposed gap?
3. Is there a defensible contribution beyond combining existing pretrained models?
4. Which accessible datasets contain genuine linked modalities and suitable event-level labels?
5. Can we construct reliable event-context ground truth without fabricating links?
6. What annotation process and adjudication budget are feasible?
7. Which languages and incident types are in scope?
8. What measurable success criteria should be set after baseline feasibility tests?

## Data questions
- Official availability, license, download size, version, and terms for each candidate dataset.
- Whether audio/video examples can be linked to specific claims/events.
- Whether redistribution is permitted or only local use.
- Whether exact/near duplicates or event leakage are present.
- Whether the labels actually measure the intended task.

## Engineering questions
- Exact Ubuntu version, Python version, disk layout, swap, and current free storage.
- Minimal dependency set compatible with the machine.
- Supported media types, size limits, durations, and language support.
- Whether a frontend is necessary for the research demonstration.
- Whether any paid or external inference service is permitted (default: do not assume it is).

## Assumptions that must not become facts
- That any named dataset is downloadable or legally reusable.
- That pretrained checkpoints run within 8 GB RAM.
- That all four modalities can be evaluated in one paired dataset.
- That event-context verification is novel.
- That confidence scores are calibrated.
- That the project is publishable before experiments and review.

## Decision rule
Resolve research and data questions before model selection. Resolve environment questions before installation/download. If a constraint blocks a planned experiment, report it and propose alternatives; do not silently change scope.
