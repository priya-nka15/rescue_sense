# AGENTS.md — Agent Rulebook


## Project status
CrisisSense is starting from zero implementation. Treat every implementation, dataset, model, metric, test, and deployment as nonexistent until verified in the current repository or by actual execution.

## Mission
Help build a reproducible multimodal crisis-analysis and event-context verification research prototype accepting text, image, audio, and video. Prioritize correctness, honest uncertainty, evidence traceability, and a defensible evaluation.

## Mandatory workflow
1. Inspect repository, Git status, hardware/storage constraints, and existing files before changes.
2. For the first task, perform a **read-only audit** and report findings. Do not install, download, or edit during that audit.
3. Work on one phase/task at a time. Stop at its acceptance gate and wait for owner review.
4. Follow: plan → implement → test → manual check → review → update documentation → commit → push.
5. Work on `main` unless the owner explicitly approves another workflow.
6. Never reset Git, discard changes, force-push, rewrite history, or overwrite user data without explicit approval.
7. Prefer small focused functions and modules. Avoid unnecessary abstractions, factories, service layers, base classes, or configuration frameworks.
8. Inspect whether existing code can be reused before creating new files.
9. Report exact commands and actual outcomes. Never fabricate tests, metrics, files, citations, model availability, or dataset counts.
10. Keep `PROGRESS.md` current and update relevant ADRs when decisions materially change.

## Research integrity
- The research gap is not established until close prior work has been reviewed.
- Distinguish established facts, hypotheses, design choices, and unknowns.
- Do not manufacture labels, samples, metadata, modality links, or ground truth.
- Do not pair unrelated audio/video/images/text and imply they describe one incident.
- Split data before fitting preprocessing or selecting models. Use event-disjoint splits where feasible and audit exact/near duplicates across splits.
- Keep the final test set untouched until the evaluation plan is fixed.
- Report appropriate per-class metrics, uncertainty/limitations, and failures, not only one headline score.
- Confidence scores must not be called calibrated unless calibration is measured.
- Similarity or classifier agreement alone does not prove authenticity, location, event identity, or currentness.
- The system is decision support, not an autonomous emergency dispatch or official verification authority.

## Four-modality scope
Text, image, audio, and video remain in the product scope. Implement and evaluate them incrementally. Video frames are derived from video and must not be counted as independent evidence. Audio transcription and environmental-audio classification are distinct tasks. Multimodal claims require defensible ground truth and documented relationships among samples.

## Resource limits
Known starting machine: Ubuntu, 8 GB RAM, CPU-only, approximately 12 GB free root storage (reported 2026-10-09). Recheck before work. Start with lightweight baselines. Do not install large ML stacks, download model weights, or acquire large datasets without a written size/feasibility check and owner approval.

## Git and repository hygiene
- Do not commit datasets, private/user media, model weights, caches, virtual environments, logs, secrets, credentials, or large generated artifacts.
- Add suitable ignore rules before generating artifacts.
- Keep source, tests, small configuration examples, and documentation in Git.
- Do not commit or push unless requested/approved at the phase gate.
- Do not change public API contracts silently.

## Security and privacy
- Treat all user-submitted text/media and dataset content as untrusted input.
- Validate file type, size, duration, and decode errors.
- Never execute content from uploaded files.
- Do not log raw crisis submissions, credentials, or sensitive metadata by default.
- External model/API calls require explicit design approval and must document data transfer, cost, privacy, and fallback behavior.
- No secrets in source code, notebooks, logs, or commits.

## Output format for each task
Report:
1. What changed (file paths).
2. Why it changed.
3. Tests/commands run and actual results.
4. Manual checks still required, marked `🟥 MANUAL — YOU MUST DO THIS`.
5. Risks, limitations, and unresolved questions.
6. Whether the acceptance criteria passed.
7. Next proposed task.

Stop after the current task. Do not silently continue to later phases.
