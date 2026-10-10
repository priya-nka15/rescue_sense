# Data Model / Schema

## Status
Proposed schema. No dataset or API format is assumed to exist yet. Revise after inspecting selected datasets and agreeing on the annotation protocol.

## Core entities

### Submission
Represents one user-submitted analysis request.
- `submission_id`: opaque internal ID; avoid embedding personal information.
- `created_at`: UTC timestamp.
- `text`: optional text.
- `media_items`: zero or more media references.
- `claimed_event`: optional structured claim, if user supplies one.
- `source_metadata`: optional, only when lawful and useful; treat as untrusted.
- `consent_and_retention`: policy state if persistent storage is implemented.

### MediaItem
- `media_id`: opaque ID.
- `modality`: `image | audio | video`.
- `mime_type`: detected/validated media type, not just file extension.
- `size_bytes`: actual size.
- `duration_ms`: audio/video when applicable.
- `sha256`: optional content hash for integrity/deduplication.
- `storage_ref`: internal reference, not a public filesystem path.
- `provenance`: known source and collection context, if documented.
- `derived_from`: parent media ID for derived artifacts, such as video frames or audio transcription.

### ModalityAnalysis
- `analysis_id`
- `media_id` or submission reference
- `task_name`
- `model_name`, `model_revision`, `preprocessing_version`
- `output`: structured task-specific result
- `warnings`
- `runtime_ms`
- `status`: `success | unsupported | failed | skipped`

### EvidenceItem
- `evidence_id`
- `source_ref`: submission, media item, external reference, or annotation
- `evidence_type`: claim, observation, metadata, external corroboration, contradiction, or missing-evidence note
- `description`
- `supports_claim`: `supports | contradicts | neutral | unknown`
- `reliability_note`
- `provenance`
- `derived_from`: for evidence derived from another item, preventing double-counting

### VerificationResult
- `status`: provisional enum `CONSISTENT | CONTRADICTED | INSUFFICIENT_EVIDENCE`
- `claim_summary`
- `supporting_evidence_ids`
- `contradicting_evidence_ids`
- `missing_evidence`
- `uncertainty_notes`
- `method_version`
- `human_review_required`: boolean
- `limitations`

Do not use `CONSISTENT` as synonymous with true/authentic, or `CONTRADICTED` as synonymous with malicious misinformation. Operational definitions must be finalized before annotation.

## Dataset manifest (recommended)
For each sample record only metadata needed for reproducibility:
- stable sample ID
- dataset/source name and version
- source split/event identifier
- available modalities
- paths or references outside Git
- label(s) and label provenance
- license/access note
- content hash where permitted
- exclusion reason, if excluded

## Annotation record
- sample ID
- claim and event identifiers
- label
- evidence/rationale
- annotator ID pseudonym or role
- annotation guideline version
- adjudication status
- ambiguity flag

## Data rules
- Never fabricate missing labels or links between modalities.
- Preserve original labels and document any mapping.
- Treat timestamps and EXIF as clues, not definitive proof.
- Never expose raw local paths or private source metadata in API responses.
- Store large media and weights outside Git.
