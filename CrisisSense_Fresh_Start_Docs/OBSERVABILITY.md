# Observability Guide

## Purpose
Observability is for debugging the application and auditing experiments, not for collecting unnecessary user data.

## Research experiment records
Record:
- experiment ID and timestamp
- code commit
- dataset/version and split manifest
- model/checkpoint revision
- preprocessing/configuration
- seed
- metrics and output artifact references
- runtime, peak memory if measurable, and failures

## Application signals (later phase)
- request count and processing status by modality
- processing latency
- decode/model failure counts
- unsupported input counts
- resource usage
- external provider failures, if applicable

## Logging rules
- Never log secrets.
- Avoid raw text, audio transcripts, images, videos, exact user locations, or other sensitive data by default.
- Use opaque request IDs.
- Sanitize untrusted values before logging.
- Keep error details useful but do not expose internal paths to clients.

## Alerts
Do not define numeric alert thresholds until normal resource and latency behavior has been measured. At minimum, surface repeated processing failures and resource exhaustion during development.
