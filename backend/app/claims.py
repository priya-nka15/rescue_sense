"""Claim extraction for multimodal crisis text, OCR, and noisy speech transcripts.

Extracts distinct, verifiable factual propositions while preserving the original wording
verbatim. Rejects non-factual conversational fillers, trivial fragments, and uninformative noise.
"""
import re
from .schemas import Claim

# Non-assertive fillers common in speech, captions, or conversational noise
FILLER_PATTERNS = {
    r'^(?:hello|hi|hey|good morning|good afternoon|good evening)\b',
    r'^(?:can you hear me|testing|check one two|one two three|mic check)\b',
    r'^(?:uh|um|er|ah|yeah|yep|nope|okay|ok|alright|thanks|thank you)\b',
    r'^(?:please subscribe|like and share|stay tuned|see you next time)\b',
}

# Verbs/predicates that indicate physical event, status, damage, or emergency action
ASSERTION_CLUES = re.compile(
    r'\b(?:is|are|was|were|has|have|had|been|became|remains|collapsed|closed|destroyed|'
    r'damaged|burning|flooded|inundated|submerged|struck|crashed|derailed|trapped|'
    r'stranded|evacuated|injured|killed|rescued|confirmed|reported|seen|spotted|rising|'
    r'blocked|falling|burst|overflowing|leaking|exploding|shut|failed|outage)\b',
    re.IGNORECASE,
)

# Crisis entity or topical indicators
CRISIS_TOPIC_CLUES = re.compile(
    r'\b(?:bridge|road|highway|street|river|dam|building|hospital|school|tower|'
    r'fire|flood|water|flames|smoke|debris|casualt(?:y|ies)|victim|people|'
    r'residents|driver|passenger|train|car|bus|plane|boat|power|gas|pipeline|'
    r'shelter|ambulance|police|firefighters?|emergency|danger|warning|alert)\b',
    re.IGNORECASE,
)


def _is_filler(text: str) -> bool:
    cleaned = text.strip().lower()
    if len(cleaned.split()) <= 2 and not CRISIS_TOPIC_CLUES.search(cleaned):
        return True
    for pattern in FILLER_PATTERNS:
        if re.search(pattern, cleaned):
            return True
    return False


def _clean_segment(text: str) -> str:
    """Normalize whitespace and strip non-semantic punctuation from edges."""
    normalized = " ".join(text.split())
    # Strip leading/trailing quotes, dashes, bullets, commas
    return normalized.strip(" \t\r\n-–—•\"'*`:,;")


def _segment_text(text: str) -> list[str]:
    """Segment punctuated written or OCR text by sentence and clause boundaries."""
    normalized = " ".join(text.split())
    # Split by standard sentence terminators (. ! ? ; and newlines) while preserving abbreviations
    raw_sentences = re.split(r'(?<=[.!?;\n])\s+', normalized)
    segments = []
    for s in raw_sentences:
        stripped = s.strip()
        if not stripped or stripped.endswith('?') or re.match(r'^(?:is|are|was|were|do|does|did|can|could|will|would|has|have|what|where|who|when|why|how)\b.*\?$', stripped, re.IGNORECASE):
            continue
        clean = _clean_segment(s).rstrip('.!')
        if clean:
            segments.append(clean)
    return segments


def _segment_transcript(transcript: str) -> list[str]:
    """Segment unpunctuated ASR transcript into meaningful candidate statements.

    ASR transcripts from local models (e.g. Vosk) lack punctuation and capitalization.
    We split on clause coordinators ('and then', 'and also', 'but', 'so', 'because')
    or pause-indicating transitions, then analyze candidates.
    """
    normalized = " ".join(transcript.split())
    if not normalized:
        return []

    # If transcript already has punctuation, use text segmentation
    if re.search(r'[.!?;\n]', normalized):
        return _segment_text(normalized)

    # Split by coordinating conjunctions when they separate long phrases
    tokens = normalized.split()
    if len(tokens) <= 8:
        return [normalized]

    parts = re.split(
        r'\b(?:and then|and also|and now|but now|because|however|meanwhile)\b',
        normalized,
        flags=re.IGNORECASE,
    )
    segments = []
    for part in parts:
        clean = _clean_segment(part)
        if clean:
            # Further split very long runs by 'and' or 'but'
            subparts = re.split(r'\b(?:and|but)\b', clean, flags=re.IGNORECASE) if len(clean.split()) > 10 else [clean]
            for sp in subparts:
                cleaned_sp = _clean_segment(sp)
                if cleaned_sp:
                    segments.append(cleaned_sp)
    return segments or [normalized]


def _evaluate_candidate(candidate: str, modality: str) -> tuple[bool, float, str]:
    """Evaluate whether candidate text constitutes a checkable factual proposition.

    Returns:
        (is_valid, confidence, extraction_method)
    """
    words = candidate.split()
    word_count = len(words)

    # Reject empty or very short non-substantive fragments
    if word_count < 3 or len(candidate) < 12:
        return False, 0.0, "too_short"

    # Reject conversational fillers
    if _is_filler(candidate):
        return False, 0.0, "conversational_filler"

    has_assertion = bool(ASSERTION_CLUES.search(candidate))
    has_crisis_topic = bool(CRISIS_TOPIC_CLUES.search(candidate))

    # Evaluate based on modality
    if modality in {"audio", "video"}:
        # Transcripts are inherently noisy. Look for semantic coherence.
        # "the bridges blows" has 3 words, subject and verb, but lacks checkable propositional context.
        # Check if the statement makes a complete verifiable claim
        if has_assertion and has_crisis_topic and word_count >= 4:
            return True, 0.75, "transcript_proposition"
        elif has_crisis_topic and word_count >= 5:
            return True, 0.60, "transcript_crisis_clause"
        elif has_assertion and word_count >= 5:
            return True, 0.50, "transcript_assertion"
        else:
            # E.g. "the bridges blows" (3 words, deformed grammar): reject as poor claim
            return False, 0.25, "noisy_speech_fragment"
    else:
        # Written text / OCR
        if has_assertion and has_crisis_topic:
            return True, 0.90, "crisis_assertion_heuristic"
        elif has_assertion or has_crisis_topic:
            return True, 0.75, "sentence_heuristic"
        elif word_count >= 4:
            return True, 0.50, "descriptive_statement"
        else:
            return False, 0.20, "insufficient_detail"


def extract_claims(text: str, modality: str, source_location: str | None = None) -> list[Claim]:
    """Extract checkable, meaningful claims from text, OCR, or speech transcripts.

    Preserves original text verbatim without inventing details.
    Filters out noisy fragments, uninformative fillers, and questions.
    """
    if not text or not text.strip():
        return []

    is_speech = modality in {"audio", "video"}
    candidates = _segment_transcript(text) if is_speech else _segment_text(text)

    claims: list[Claim] = []
    seen: set[str] = set()

    for candidate in candidates:
        candidate_clean = _clean_segment(candidate)
        normalized_key = candidate_clean.casefold()
        if not candidate_clean or normalized_key in seen:
            continue

        is_valid, confidence, method = _evaluate_candidate(candidate_clean, modality)
        if is_valid:
            seen.add(normalized_key)
            claims.append(Claim(
                text=candidate_clean,
                modality=modality,
                source_location=source_location,
                extraction_method=method,
                extraction_confidence=round(confidence, 2),
            ))

    # If written text didn't match strict rules, fall back to preserving clean sentences
    if not claims and not is_speech and len(text.strip()) >= 5:
        first_sentence = _clean_segment(text.split('.')[0])
        if len(first_sentence) >= 5 and not _is_filler(first_sentence):
            claims.append(Claim(
                text=first_sentence,
                modality=modality,
                source_location=source_location,
                extraction_method="sentence_heuristic",
                extraction_confidence=0.60,
            ))

    return claims[:8]
