# Prompt / Skill Library

Use one prompt per phase. Give the agent repository access only when needed. Never use prompts to bypass project rules in `AGENTS.md`.

## Prompt 1 — Read-only audit
```text
Read AGENTS.md and the planning docs. Perform a READ-ONLY audit of the current repository, Git status, OS/Python/Git versions, RAM/swap, free disk, and existing data/model artifacts. Do not edit, install, download, reset Git, or commit. Separate verified facts from assumptions. Report exact commands and outcomes, blockers, and the next proposed phase. Stop.
```

## Prompt 2 — Literature review
```text
Investigate original papers and official repositories on multimodal crisis analysis, out-of-context crisis media, recycled-media verification, and event-context consistency. Build a table of task, dataset, labels, method, evaluation, limitations, and overlap with CrisisSense. Cite original sources and mark uncertain claims. Do not claim novelty. Recommend a precise research question and stop.
```

## Prompt 3 — Dataset feasibility review
```text
For each candidate dataset, verify its official source, version, access, license, size, modalities, labels, provenance, and suitability for the stated research question. Check whether modalities are genuinely linked. Propose a leakage-resistant split and annotation protocol. Do not download anything yet. Report blockers and stop.
```

## Prompt 4 — Implement one baseline
```text
Implement only the approved baseline phase. Inspect existing files before adding new ones. Use the approved dataset/split and a lightweight method. Fit preprocessing on training data only. Save predictions and configuration, report actual metrics, add focused tests, and document runtime/memory. Do not add other modalities or features. Update PROGRESS.md and stop.
```

## Prompt 5 — Independent review
```text
Review the latest changes for correctness, data leakage, metric validity, reproducibility, unsafe media handling, dependency growth, and regressions. Cite file/line evidence. Do not refactor working code for style alone. Fix only confirmed in-scope defects if authorized, rerun tests, report actual results, and stop.
```

## Prompt 6 — Phase handoff
```text
Update PROGRESS.md with phase, files changed, decisions/ADRs, exact commands, actual test/experiment outcomes, manual actions, blockers, acceptance criteria status, and next task. Do not mark unrun checks complete. Do not commit or push unless explicitly approved. Stop.
```

## Required response footer for coding agents
- Changes:
- Tests/commands and actual outcomes:
- 🟥 MANUAL — YOU MUST DO THIS:
- Risks/open questions:
- Acceptance criteria status:
- Next proposed task:
