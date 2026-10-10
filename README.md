# CrisisSense

Local, evidence-aware review software for crisis-related text, images, audio, and video. It is decision support: it never treats a classifier, OCR result, transcript, or missing search result as proof of truth.

## Current capability

- Text: sentence-level claim candidates and local-evidence matching. The optional all-MiniLM-L6-v2 adapter can use only pre-existing local weights; embedding similarity is not a truth score.
- Image: safe decode, dimensions, integrity hash, optional local Tesseract OCR, an optional accompanying claim, and an optional MobileNetV3-Small feature adapter that uses only pre-existing local weights. Visual features are not evidence of event identity, time, location, or authenticity.
- Audio: bounded upload validation, WAV metadata, and cache-only Vosk transcription when the local model is available. Silent input is reported as no speech; transcripts are observations, never proof.
- Video: bounded local FFmpeg/ffprobe container validation, timestamped frame sampling, and optional audio extraction/transcription. Frames and decoded audio are observations, never proof of authenticity.
- Verdicts: the shipped pipeline abstains with `INSUFFICIENT_EVIDENCE` unless an explicitly configured evidence method can justify another relationship. Confidence is not calibrated.
- Research: group/duplicate split validation and metric/report utilities are implemented; no VERITE asset or result is included.

## Local setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt pytest==8.3.4 httpx==0.28.1
cd frontend && npm install
```

Optional CPU-only local feature extractors are installed separately, after the base backend is verified:

```bash
.venv/bin/pip install -r backend/requirements-ml-cpu.txt
```

The CPU PyTorch index is declared in that file. The application never downloads a model during a request: approved checkpoints must already be in the local Hugging Face or Torch cache.

For the optional local ASR adapter:

```bash
.venv/bin/pip install -r backend/requirements-media.txt
```

The Vosk adapter requires a separately acquired, lawfully usable model directory; configure it with `CRISISSENSE_ASR_PATH` or place it under `data/models/vosk-model-small-en-us-0.15`. Project-local FFmpeg/ffprobe, when present under `data/tools/usr/bin`, are used before no decoder is reported.

Run the backend from the repository root:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Run the frontend in a second terminal:

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173`. The backend is available at `http://localhost:8000`; API documentation is at `/docs`.

For an offline expo run, set these variables before starting the backend so no model lookup attempts the network:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CRISISSENSE_ASR_PATH="$PWD/data/models/vosk-model-small-en-us-0.15"
```

The backend expects port `8000` and the Vite development server expects port `5173`. If a port is occupied, stop the old process or choose another port and update the frontend `VITE_API_URL` accordingly. Localhost, loopback, and private-network browser origins on these ports are accepted; public origins remain rejected. If the frontend shows `Service unavailable` or `/api/health` returns a proxy error, start the backend first and confirm `curl http://127.0.0.1:8000/api/health` returns `{"status":"ok","version":"0.1.0"}`. If status reports `video_decoder: false`, confirm `data/tools/usr/bin/ffmpeg` and `ffprobe` exist or install FFmpeg through the operating system; no decoder is downloaded by the application. If transcription reports unavailable, confirm Vosk is installed and `CRISISSENSE_ASR_PATH/am/final.mdl` exists. Missing model caches intentionally degrade to explicit unavailable/insufficient-evidence states rather than downloading at request time.

## Tests

```bash
.venv/bin/python -m pytest -q backend/tests research/tests
cd frontend && npm test
cd frontend && npm run build
```

Latest verification: backend/research tests: `40 passed` (four scikit-learn deprecation warnings); localhost HTTP integration: `5 passed`; frontend Vitest: `4 passed`; `npm run build` passed. An isolated HTTP smoke test submitted real text, image, synthetic speech WAV, and synthetic MP4 inputs. Vosk transcribed the WAV as `the bridges closed`; this demonstrates local ASR execution, not accuracy. The integration suite exercises evidence verdicts, text lifecycle/history deletion, image features, audio status, malformed-video rejection, and security/input validation. Browser automation remains untested because this execution environment has no controllable browser surface.

## Data, models, and privacy

Uploads are processed in memory and are not kept as application files. The SQLite database stores results and metadata, not raw media. `data/`, `.venv/`, model caches, and frontend dependencies are ignored.

No model weights, datasets, external search credentials, or VERITE data are bundled. VERITE is gated and must only be acquired after authorized access under its terms. The application remains usable without it.

The tested CPU-only environment uses Python 3.11.9, Torch `2.5.1+cpu`, Torchvision `0.20.1+cpu`, and Sentence Transformers `3.4.1`; it is about 1.4 GB. The adapters refuse to fetch weights during requests. all-MiniLM-L6-v2 revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` is cached locally (88 MB) and was tested offline: two 384-dimensional embeddings took 665 ms after a 358 ms load. MobileNetV3-Small `IMAGENET1K_V1` is cached locally (9.9 MB) and produced a 576-dimensional feature vector from a generated image in 2,120 ms after model loading. These features are not factual verdicts.

System FFmpeg is not installed because this environment requires interactive `sudo` authentication. A project-local FFmpeg/ffprobe bundle is used for bounded decoding, and Vosk 0.3.45 plus the small English model are available under ignored local data. The worker permits 2.25 GiB virtual address space because the Vosk model maps about 1.65 GiB while using about 170 MB resident memory; it still has a 55-second CPU limit, a 60-second wall timeout, a 64 MiB output limit, and single-job processing. The application never downloads models during requests.

## Evidence configuration

Evidence retrieval reads the local SQLite collection and can fetch user-supplied public HTTP(S) URLs with strict DNS/private-network checks, redirect validation, an 8-second timeout, an approximately 1 MB body cap, and HTML-only parsing. No search provider or API key is configured, so the application does not search the open web. Fetched pages are contextual until a reviewer binds an exact passage to a claim; retrieval or similarity alone never produces `SUPPORTED` or `CONTRADICTED`. If DNS/connectivity or a source page fails, the result preserves the failure and abstains with `INSUFFICIENT_EVIDENCE` when no reviewed relationship exists.

## Research evaluation status

No benchmark result is claimed yet. The evaluation runner is ready for an authorized JSON manifest:

```bash
PYTHONPATH=. .venv/bin/python -m research.run path/to/authorized_manifest.json --output results/report.json
```

It requires dataset provenance, license, labels, non-empty train/validation/test splits, and sample grouping fields. It rejects duplicate IDs and cross-split event, source, claim, image-hash, and image-cluster leakage. It reports majority and train-only TF-IDF + Logistic Regression baselines, accuracy, per-class precision/recall/F1, macro-F1, confusion matrices, coverage, and selective accuracy.

The evaluation is currently blocked on an appropriate licensed benchmark. The official CrisisMMD page reports an approximately 1.8 GB v2.0 download and labels for informativeness, humanitarian category, and image damage severity; those are crisis-response classification labels, not truth-verification ground truth. The official VERITE repository documents 1,000 image-text pairs with Truthful, Miscaptioned, and Out-of-Context labels, but it is a non-crisis benchmark and its July 2026 notice requires an academic or research-institution email for raw-image access. MediaEval's verification task is relevant, but the surviving social-media assets and third-party rights do not currently provide a reproducible event-disjoint acquisition for this machine. No benchmark data was downloaded and no research metrics were produced.
