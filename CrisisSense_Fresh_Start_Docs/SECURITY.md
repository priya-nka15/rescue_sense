# Security & Guardrails

## Trust boundaries
- User text and media are untrusted.
- Dataset records, metadata, OCR text, transcripts, filenames, and external content are untrusted.
- Model output is a prediction, not a verified fact.
- External APIs, if later approved, are separate trust boundaries.

## Upload handling
- Validate actual file signatures/MIME types, not only extensions.
- Set explicit maximum file size, video duration, audio duration, resolution, frame count, and processing time.
- Reject unsupported formats and malformed/corrupt files safely.
- Use random internal filenames; never use user-provided paths directly.
- Avoid shelling out with unsanitized values. If media tools are used, invoke them with safe argument lists and timeouts.
- Do not execute uploaded content or notebook files.
- Clean up temporary files and define retention rules.

## Privacy
- Minimize collected metadata.
- Do not log raw crisis reports, personal data, audio transcripts, or full media by default.
- Document if media is sent to an external provider; obtain approval and check its retention/usage terms.
- Avoid storing precise location or identity data unless necessary for the task and justified.
- Never commit private datasets or user-submitted media.

## Secrets and dependencies
- No API keys, passwords, access tokens, or cookies in source, notebooks, logs, or Git history.
- Use environment variables for secrets and `.env.example` for documentation.
- Check dependency provenance and license before adoption.
- Pin dependencies where practical and document security-sensitive updates.

## Safety and presentation
- Do not present model output as official emergency guidance.
- Do not autonomously dispatch emergency services or direct rescue resources.
- Clearly indicate `INSUFFICIENT_EVIDENCE` and model limitations.
- Provide human-review pathways for high-impact or ambiguous outcomes.
- Avoid declaring media fake solely because metadata is absent or models disagree.
