# Environment & Configuration Guide

## Current known environment
- OS: Ubuntu (exact release/version must be rechecked).
- RAM: 8 GB reported.
- GPU: CPU-only reported.
- Root filesystem: 98 GB total, 82 GB used, 12 GB available as of 2026-10-09.
- Python/Git versions: not yet recorded.

## Phase 0 commands
Run from a terminal and save output in your private notes:
```bash
pwd
git status --short --branch
git log -1 --oneline
python3 --version
git --version
free -h
df -h
du -sh . 2>/dev/null
```
Do not paste secrets or private paths unnecessarily.

## Environment principles
- Do not install packages until the read-only audit and Phase 1 plan are approved.
- Use a project virtual environment after Python/dependency compatibility is chosen.
- Pin direct dependencies once the minimal stack is selected; avoid installing both TensorFlow and PyTorch by default.
- Prefer CPU-compatible packages and avoid GPU-only requirements.
- Store large datasets/checkpoints outside Git and preferably outside the root disk if storage is constrained.
- Keep `.env` local and ignored; commit only `.env.example` with placeholder names, never real values.
- Document exact setup, run, test, and cleanup commands after they have been tested.

## Configuration
Use environment variables only for true environment-specific settings or secrets. Do not build a large configuration framework prematurely. Validate required settings at startup and provide safe defaults where appropriate.

## Reproducibility
Record Python version, dependency versions, model revisions, dataset versions, split manifest IDs, seeds, and commands used to generate results.
