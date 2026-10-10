# SIC Capstone Alignment — CrisisSense

## Purpose
Use the three provided SIC proposals as structural and quality templates, not as technical designs to copy:
- Long-Horizon Agent Evaluation
- Adaptive Attack Chain Mitigation and Validation in Agentic AI Systems
- Graph-Based Early Warning System for Cascading Failures in Critical Infrastructure

CrisisSense remains a distinct project: multimodal crisis intelligence and evidence-aware event-context verification for text, images, audio, and video.

## Alignment assessment
This is a planning assessment, not a claim that implementation or research validation is complete.

| Proposal template element | CrisisSense status | Required next action |
|---|---|---|
| Executive summary and problem statement | Partially specified in PRD | Refine after literature review |
| Objectives | Broad goals exist | Convert into testable objectives |
| Research gap and contribution | Not established | Compare closest prior work before novelty claims |
| Scope and feasibility | Four modalities required; resource constraints known | Stage modalities and confirm data/compute feasibility |
| Methodology | Proposed workflow only | Define method after data and labels are verified |
| Data acquisition and provenance | Not complete | Verify sources, licences, labels, provenance, and sample linkage |
| Baselines and comparative experiments | Planned | Select task-appropriate baselines |
| Quantitative evaluation | Planned | Set metrics and split protocol from research question |
| Ablation and error analysis | Planned in task structure | Test each component and inspect failures |
| Explainability and uncertainty | Requirement identified | Return traceable evidence and avoid unsupported certainty |
| Application/demo | UI spec exists at planning level | Build after the research pipeline stabilizes |
| SIC curriculum alignment | Proposed below | Check against actual syllabus and instructor rubric |
| Reproducibility | Documentation requirements exist | Verify clean setup and repeatable runs |
| Risks and mitigation | Guardrails exist; formal risk register still needed | Track likelihood, impact, mitigation, trigger, fallback |
| Research paper | Planned | Use actual results and verified citations only |

## What to learn from each template without copying its project

### 1. Long-Horizon Agent Evaluation
**Borrow:** diagnostic rather than outcome-only evaluation; clear task definitions; graded evaluation where appropriate; failure analysis; reproducibility; an interactive demonstration; explicit alignment to course modules.

**CrisisSense adaptation:** evaluate text, image, audio, and video components separately and in combinations. Inspect false matches, false contradictions, missing evidence, and modality failures. Use per-class metrics, event-disjoint testing where feasible, ablations, and human review of ambiguous annotations.

**Do not copy:** long-horizon agent tasks, agent trajectory metrics, memory/goal-drift dimensions, or dense rewards as if they were CrisisSense's research method.

### 2. Adaptive Attack Chain Mitigation
**Borrow:** explicit architecture, a testable system loop, knowledge-grounded decisions, controlled test scenarios, validation after action, risk analysis, and comparisons against a simpler baseline.

**CrisisSense adaptation:** input → modality-specific observations → evidence/provenance checks → verification decision → uncertainty/human review. Evaluate whether evidence-aware verification improves over classification-only or similarity-only baselines.

**Do not copy:** attack-chain threat models, security invariants, attack graphs, attack simulations, or mitigation controllers; they solve a different problem.

### 3. Graph-Based Early Warning
**Borrow:** clearly defined prediction targets, data provenance, baseline comparisons, quantitative metrics, robustness checks, explainability, ablation studies, and staged scope.

**CrisisSense adaptation:** define exactly what event-context consistency means; use labelled examples with defensible provenance; report metrics appropriate to classification, retrieval, calibration, and abstention; test generalization across events where possible.

**Do not copy:** power-grid graphs, cascade simulation, GNNs, infrastructure failure labels, or simulator speed-up claims unless an independently justified CrisisSense question requires them.

## SIC curriculum mapping (provisional)

| SIC learning area | CrisisSense activity | Deliverable/evidence |
|---|---|---|
| Python and libraries | Data inspection, preprocessing, manifest validation, evaluation scripts | Tested and documented data pipeline |
| Probability and statistics | Split design, confidence intervals where feasible, calibration/uncertainty evaluation, error analysis | Reproducible statistical evaluation report |
| Supervised learning | Lightweight text/image/audio/video baselines where data supports them | Baseline metrics and saved predictions |
| Unsupervised learning (if useful) | Explore embeddings or cluster failure patterns only if relevant | Justified exploratory report; not mandatory |
| Deep learning / pretrained models | Reuse and evaluate selected pretrained models within resource constraints | Model comparison with version/provenance |
| Multimodal reasoning | Compare individual modalities and evidence-fusion variants | Ablation table and error analysis |
| Application/capstone | Present input, evidence, uncertainty, and provisional result | Tested demo/API after research pipeline works |
| Research practice | Related-work review, annotation protocol, reproducible experiments, manuscript preparation | Research brief and evidence-supported paper draft |

This mapping is proposed, not an official SIC syllabus mapping. Verify against the actual course modules and instructor rubric.

## Minimum research evidence expected
1. A defined research question and related-work table.
2. Dataset inventory with provenance, licence/access, labels, and modality linkage.
3. Written annotation and split protocol.
4. Baseline results from actual runs.
5. Comparison of the proposed method with baselines.
6. Error analysis, ablations, and limitations.
7. Reproducible configuration and commands.
8. A working demo whose claims match the evidence.

## Decision gate
CrisisSense is structurally aligned with the type of capstone planning represented by the proposals, but it is not yet research-validated. The next gate is literature review and data feasibility, not model implementation. If available data cannot support valid linked four-modality evaluation, keep all four modalities in product scope but explicitly limit which modalities are evaluated together in the core experiment.
