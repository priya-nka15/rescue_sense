# Progress / Handoff Log

## Latest reliability verification

54 backend/research/HTTP tests and 4 frontend tests passed; production build and dependency consistency check passed. Fixed fetched provenance, later-passage retrieval, conflicting-review truncation, malformed charset handling, and speech after initial silence. Isolated backend/Vite servers verified public URL retrieval, OCR/visual features, Vosk speech, video frames, persistence, and malformed-input recovery. README records startup commands and limits. No browser visual check or independent benchmark accuracy result is claimed.

## Current state
**Project status: local CPU implementation and verification completed; independent research evaluation is blocked on benchmark access and label fit.**

As of 2026-10-09, the user has stated that no previous implementation should be relied upon and wants to build CrisisSense from scratch. The earlier local machine details reported are Ubuntu, 8 GB RAM, CPU-only, and approximately 12 GB free root storage. Recheck these before resource-intensive work.

## Verified completed implementation
- FastAPI/SQLite local service, bounded four-modality request paths, result persistence, and research evaluation utilities were implemented.
- Backend/research tests passed: `40 passed` with four scikit-learn deprecation warnings; evaluation utility tests alone passed `8`.
- Frontend Vitest passed `4`; production build passed; isolated localhost integration passed `5`.
- CPU-only MiniLM, MobileNetV3-Small, Vosk speech recognition, and project-local FFmpeg/ffprobe were executed in bounded smoke tests.
- No benchmark dataset was downloaded and no research performance metrics were produced.

## Current phase
Research evaluation readiness. The runner is implemented, but an authorized crisis truth-verification benchmark is not locally available.

## Decisions currently in force
- Scope includes text, image, audio, and video.
- Build locally on the user's Ubuntu system unless the user changes this decision.
- Prefer pretrained models and lightweight baselines; do not train foundation models from scratch by default.
- Do not install large dependencies or download datasets/checkpoints until storage, license, task fit, and resource requirements are reviewed.
- Research novelty and benchmark performance are not established.
- Work on `main` unless explicitly changed.
- Implement one phase at a time and stop at each acceptance gate.

## Completed tasks
- Fresh-start documentation pack reviewed.
- Local implementation, CPU model smoke tests, evidence-path tests, frontend build, and four-modality HTTP checks completed.
- Evaluation runner records provenance, manifest hash, seed, split counts, predictions, classification metrics, coverage, and leakage errors.

## Commands and test results
- `PYTHONPATH=. .venv/bin/pytest -q backend/tests/test_api.py backend/tests/test_evidence.py backend/tests/test_limits.py research/tests` — `40 passed`.
- `PYTHONPATH=. .venv/bin/pytest -q research/tests` — `8 passed`.
- `.venv/bin/python -m compileall -q backend research` — passed.
- `.venv/bin/pip check` — no broken requirements.
- `timeout 5 .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8011 --lifespan off` — started successfully, then shut down after the smoke-test timeout.

## Blockers / unknowns
- No authorized crisis benchmark with truth-verification labels is available locally.
- CrisisMMD is approximately 1.8 GB and its labels are crisis-response categories, not truth verification.
- VERITE has relevant image-text labels but is non-crisis and current raw-image access requires institutional verification.
- MediaEval asset retrievability, event-disjoint balance, and third-party media rights remain blockers.
- Supported file formats, languages, annotation protocol, and numeric success criteria not yet decided.

## Next action
Obtain lawful access to a benchmark whose labels match claim/media verification, then create an event/source/image-disjoint manifest and run `PYTHONPATH=. .venv/bin/python -m research.run ...`. Do not run or report benchmark metrics before that access and label review.

## Handoff template
At each phase completion, append:
- Date:
- Phase:
- Changes:
- Commands run:
- Actual test/results:
- Manual actions required:
- Decisions/ADRs:
- Known issues:
- Acceptance criteria status:
- Recommended next phase:
