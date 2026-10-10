# UI/UX Specification

## Status
Proposed; UI implementation is deferred until the research output schema and API are stable.

## Primary user flow
1. User enters a crisis claim as text.
2. User optionally adds image, audio, and/or video.
3. UI shows supported formats, size/duration limits, and privacy notice.
4. User submits for analysis.
5. UI displays modality-specific observations separately.
6. UI displays evidence supporting the claim, evidence contradicting it, missing evidence, and uncertainty.
7. UI presents a provisional result and recommends human review for ambiguous/high-impact cases.

## Result language
Use cautious language:
- `CONSISTENT`: available evidence is compatible with the defined claim, not proof of authenticity.
- `CONTRADICTED`: available evidence conflicts with the defined claim, with the conflict explained.
- `INSUFFICIENT_EVIDENCE`: evidence cannot support a reliable decision.

Final labels and definitions require research-owner approval before annotation.

## UX requirements
- No visual treatment that makes uncertain predictions look official.
- Always distinguish model observations from externally verified facts.
- Show which modality produced each evidence item.
- Show warnings when a modality was skipped, unsupported, or failed.
- Do not imply audio/video were analysed if processing did not complete.
- Accessible labels, keyboard navigation, readable error messages, responsive layout.
- Avoid excessive charts/cards; prioritize clear evidence and limitations.

## Out of scope initially
- Public social feed ingestion.
- Emergency dispatch workflow.
- User accounts and persistent personal histories unless required and security-reviewed.
