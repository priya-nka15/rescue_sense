# CI/CD & Deployment Runbook

## Status
No CI or deployment is configured by this document. Add it only after the repository and first minimal test suite exist.

## Initial CI scope
A later CI workflow should:
1. Check out source.
2. Install the minimal pinned dependency set.
3. Run formatting/lint checks if configured.
4. Run unit tests that do not require large model downloads.
5. Validate documentation/schema or API smoke tests where appropriate.
6. Report failures without exposing secrets.

## CI restrictions
- Do not download large datasets/model checkpoints during ordinary CI.
- Do not include secrets in workflow files or logs.
- Do not run destructive cleanup commands against shared storage.
- Keep optional integration tests separate from fast default tests.
- Use least-privilege tokens and pin third-party actions where practical.

## Deployment
Deployment is out of scope until API behavior, data handling, inference resources, and privacy requirements are known. Before deployment, document supported inputs, limits, model hosting, costs, data retention, rollback, and human-review behavior.

## Release checklist
- Tests pass in a clean environment.
- API contract documented.
- Model and dataset licenses reviewed.
- No secrets or restricted data in repository.
- Error handling and input limits tested.
- Limitations and intended use visible.
- Deployment and rollback commands tested.
