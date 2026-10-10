# Implementation Status

## Member 1 and Member 2 integration

- Added `backend/app/analysis.py`, a transparent CPU-only heuristic extractor for crisis language, seven incident classes, location phrases, severity clues, response needs, and temporal expressions. It returns structured `crisis_analysis` and `currentness` fields without changing reviewer-scoped verdict logic.
- Text, OCR, and Vosk transcript text feed the same analysis object. Video keeps timestamped frame observations separate. Cached MiniLM, MobileNetV3-Small, Tesseract, FFmpeg, and Vosk behavior is preserved.
- The frontend displays incident, location, severity, needs, and currentness clues with explicit uncertainty. No calibrated confidence or authenticity decision is added.
- Acceptance examples covered fire, flood, accident, earthquake, medical emergency, infrastructure failure, non-crisis text, hypothetical wording, missing and multiple locations, severity extremes, multiple needs, old/relative/multiple date clues, OCR, speech, and video observations. Multiple location/date clues remain structured and qualified for review.

## Latest reliability pass

- Full backend/research suite, including five real HTTP integration tests: 54 passed, 5 deprecation warnings. Frontend: 4 passed; production build passed; pip check found no broken requirements.
- Fixed fetched-text hashes/final URLs, retrieval beyond 4,000 characters, truncation of conflicting reviewer annotations, unsupported page charset handling, and ASR dropping speech after a silent opening.
- Regression tests cover each backend fix. Frontend tests verify evidence-to-claim attribution and source link rendering using mocked responses.
- Started isolated backend and frontend servers and verified the actual Vite API proxy. Live example.com retrieval returned contextual evidence with provenance and abstained. Generated notice OCR extracted its claim; visual features ran; Vosk transcribed speech after a three-second silent intro as `the bridges closed`; local video extraction returned a frame at 0 ms. All four results persisted. Malformed image/audio/video uploads failed and service health recovered.
- Validation servers were stopped. No model/dataset downloads or installations were performed. Browser visual interaction and independent research accuracy remain untested. Audio uses Python 3.11's deprecated audioop; do not assume Python 3.13 compatibility.

## Verified locally

- Python 3.11 virtual environment with the pinned backend dependencies.
- FastAPI application with health, readiness, status, job, history, configuration, and four modality submission routes.
- SQLite schema initialization and result/history persistence without storing raw uploads.
- Text claim extraction, local evidence collection matching, and an evidence-first abstention result.
- Safe image decoding, integrity hashing, optional Tesseract OCR, bounded audio validation, WAV metadata extraction, and bounded FFmpeg media decoding through the project-local tool bundle.
- Research utilities for source-group and exact-image-hash leakage detection, grouped split assignment, and reproducible classification metrics.
- Backend/research tests: `40 passed, 4 warnings`.
- Real local HTTP integration: `5 passed` for evidence verdicts, text lifecycle/history, image features, audio status, malformed-video failure, and input/security validation.
- Uvicorn startup smoke test passed.
- Frontend verification: Vitest `4 passed`; `npm run build` passed.
- Text preprocessing, optional-image-claim handling, lazy model availability reporting, and a train-only TF-IDF + Logistic Regression research baseline are implemented.
- Evidence retrieval now supports user-supplied public HTTP(S) URLs through bounded HTML fetches with redirect, DNS/private-network, timeout, content-type, and response-size checks. Retrieved pages are labeled contextual/unverified; only exact reviewer annotations can produce support or contradiction.
- Research evaluation runner is implemented but no benchmark experiment was run: no locally available dataset satisfies the crisis-domain, truth-verification, licensing, and reproducible split requirements simultaneously.

## Deliberate limitations

- The configured evidence collection is initially empty. No online retrieval provider is enabled, so the application abstains with `INSUFFICIENT_EVIDENCE` rather than fabricating evidence or claims.
- No search API key or web-search provider is configured. Shell DNS was unavailable during this check, so a live external page could not be fetched from this environment; fetch failures are surfaced as evidence gaps and do not create citations.
- A Vosk small English model is present under the ignored local `data/models` directory and is used cache-only. A generated 16 kHz mono PCM fixture containing “the bridge is closed” completed through the bounded worker in 2.435 seconds and produced “the bridges closed.” Silent audio is handled as a completed no-speech observation. This confirms ASR execution, not transcription accuracy, and transcripts are never factual evidence.
- System FFmpeg was not installed because `sudo apt-get install ffmpeg` required interactive authentication. A verified project-local FFmpeg/ffprobe bundle is used instead for bounded video frame extraction and audio decoding. A 13-second fixture yielded the configured maximum of 12 timestamped frames; a 181-second fixture and malformed bytes were rejected. No frame proves event authenticity.
- VERITE is not included and no experiment scores are claimed. Its access remains gated.
- CrisisMMD's official distribution is approximately 1.8 GB and its documented v2.0 labels concern informativeness, humanitarian category, and image damage severity; these cannot be used as truth-verification labels without a new annotation protocol. VERITE documents 1,000 non-crisis image-text pairs with Truthful, Miscaptioned, and Out-of-Context labels, but its current raw-image access requires institutional-email verification. MediaEval remains limited by media retrievability, event/split concerns, and third-party content rights.
- all-MiniLM-L6-v2 and MobileNetV3-Small are local-cache-only adapters with approved local weights and tested CPU inference. MiniLM revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` produced two 384-dimensional embeddings in 665 ms after a 358 ms load; MobileNetV3-Small produced a 576-dimensional feature vector in 2,120 ms after model loading. Their outputs remain retrieval/visual features, never verification verdicts.

## Frontend verification

The frontend dependency lockfile is present and React TypeScript declaration packages are pinned. `npm run build` passed, producing the Vite distribution. Vitest has four focused tests for text result rendering, image-upload request errors, history deletion, and reviewer-scoped evidence/provenance rendering.

No browser automation surface was available in the execution environment, so visual interaction and all four tabs were not browser-tested. The Vitest assertions render React components in JSDOM, rather than a real browser.

`npm audit --omit=dev --audit-level=high` could not complete because DNS resolution for the npm audit endpoint returned `EAI_AGAIN`. No dependency upgrade was attempted.

## Resource snapshot

At the acceptance check: 19 GB root disk free; about 3.0 GiB RAM available; 4.0 GiB swap total with about 2.0 GiB free; virtual environment size 1.4 GB; local Vosk model 68 MB; and frontend dependencies 129 MB. The worker address-space cap is 2.25 GiB because Vosk maps about 1.65 GiB virtually despite a measured resident set near 170 MB. These constraints do not justify adding a larger ASR stack.

## Phase 8 model audit

- `sentence-transformers/all-MiniLM-L6-v2`: Apache-2.0; 22.7M parameters; 384-dimensional sentence embeddings. It is intended for semantic search/retrieval, not truth classification.
- `torchvision.models.mobilenet_v3_small` with `IMAGENET1K_V1`: 2,542,856 parameters; documented 9.8 MB weights; intended here only as a visual feature extractor.
- The current Python environment contains CPU-only Torch 2.5.1+cpu, Torchvision 0.20.1+cpu, Sentence Transformers 3.4.1, and Vosk 0.3.45. `torch.cuda.is_available()` returned `False`; the CPU inference measurements above are actual executions.
- The frontend source has four Vitest tests; `npm test -- --run` passes. The production build passes.

## Research evaluation readiness

`research.run` accepts only an explicitly authorized JSON manifest and records the manifest SHA-256, dataset/version/source/license, labels, seed, split counts, predictions, and leakage validation. The included synthetic manifest is a unit test fixture only and is not a research result. No independent crisis benchmark has been evaluated, so accuracy, precision, recall, macro-F1, confusion matrices, coverage, and abstention metrics for CrisisSense remain unreported.

Required manual blocker: obtain lawful access to a benchmark whose labels actually represent claim/media verification, preserve its license and provenance terms, and construct a leakage-audited event/source/image-disjoint manifest before running `research.run`.
