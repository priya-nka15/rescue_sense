# Product Requirements Document — CrisisSense

## 1. Status
Draft for research planning. Requirements are provisional until Phase 0 and the literature/data feasibility review are complete.

## 2. Product summary
CrisisSense is a multimodal crisis-intelligence and evidence-aware event-context verification prototype. It accepts text, images, audio, and video and helps users inspect crisis-related claims alongside supporting, conflicting, and missing evidence.

## 3. Problem
During emergencies, reports and media can be incomplete, duplicated, outdated, misleading, or disconnected from the event they claim to depict. A classifier that detects a disaster category is not sufficient to establish where or when media originated. Users need a system that communicates what the evidence does and does not support.

## 4. Intended users
- Researchers evaluating crisis-related information extraction and media verification.
- Analysts or trained reviewers examining incoming reports.
- Demonstration users testing the research prototype.

The prototype is not an official emergency service and must not be represented as a replacement for human verification.

## 5. Core goals
1. Accept text, image, audio, and video inputs through a documented interface.
2. Extract modality-specific information using appropriate lightweight or pretrained models where feasible.
3. represent evidence, contradictions, missing information, and uncertainty explicitly.
4. Evaluate modality-specific and multimodal methods against clear baselines.
5. Produce reproducible experiments, documented limitations, and traceable outputs.
6. Operate within the known local constraint of 8 GB RAM, CPU-only, and about 12 GB free disk unless later resources are confirmed.

## 6. Non-goals for the initial research prototype
- Autonomous dispatch, rescue prioritisation, or official emergency alerts.
- Guaranteeing that media is authentic, geolocated, or current without suitable evidence.
- Training large foundation models from scratch.
- Supporting every file format or every language from the first iteration.
- Claiming novelty or publication readiness before a literature review and experiments.
- Forcing all four modalities into a single experiment if appropriate paired/linked data is unavailable.

## 7. Proposed core workflow
1. User submits text and optional media (image, audio, video).
2. Validate format, size, duration, and processing constraints.
3. Run modality-specific extraction/classification.
4. Link evidence only where provenance or annotation justifies the relationship.
5. Evaluate the claim against available contextual evidence.
6. Return a provisional status such as `CONSISTENT`, `CONTRADICTED`, or `INSUFFICIENT_EVIDENCE`, with reasons and limitations.
7. Human reviewer can inspect evidence and correct/annotate outcomes in the research workflow.

These status labels are provisional and must be defined operationally before annotation and evaluation.

## 8. Functional requirements
- FR-01: Accept text input.
- FR-02: Accept image input and safely decode supported formats.
- FR-03: Accept audio input and run a documented transcription and/or audio-analysis pipeline.
- FR-04: Accept video input and run a documented frame/temporal analysis pipeline.
- FR-05: Return structured outputs with evidence sources, uncertainty, and failure/unsupported states.
- FR-06: Clearly separate classification, event-context consistency, and currentness.
- FR-07: Provide a repeatable evaluation command and persist metrics/configuration.
- FR-08: Record model/dataset versions and preprocessing details.
- FR-09: Handle missing modalities without fabricating evidence.
- FR-10: Expose a documented API; frontend is a later phase after core research validity.

## 9. Non-functional requirements
See `NON_FUNCTIONAL_REQUIREMENTS.md`.

## 10. Research requirements
- Compare against simple, appropriate baselines.
- Use leakage-resistant splits; event-disjoint evaluation where feasible.
- Include per-class metrics, error analysis, and ablations.
- Use an annotation protocol for event-context labels, with independent review/adjudication where feasible.
- Report confidence calibration only if measured.
- Report limitations and negative results honestly.

## 11. Success criteria
Success criteria and numeric targets are not set yet. They must be defined after dataset inspection and related-work review; do not invent thresholds now. At minimum, success requires a reproducible baseline, an evaluation design that matches the research question, and evidence that the proposed method adds value over selected baselines.

## 12. Open dependencies
Research gap, datasets, licenses, available compute, supported file types, languages, model checkpoints, annotation budget, and deployment target remain open. Track them in `OPEN_QUESTIONS.md`.
