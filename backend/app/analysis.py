"""Transparent, CPU-only crisis text analysis baselines.

These rules extract clues for review. They are not calibrated classifiers and
never change the evidence-based verdict.
"""
import re
from datetime import datetime, timezone

INCIDENT_PATTERNS = {
    'flood': r'\b(flood|flooding|inundat|waterlogged|heavy rain)\b',
    'fire': r'\b(fire|blaze|burning|smoke)\b',
    'accident': r'\b(accident|collision|crash|crashed|wreck)\b',
    'earthquake': r'\b(earthquake|tremor|seismic)\b',
    'medical_emergency': r'\b(medical|ambulance|injur(?:y|ies)|hospital|heart attack)\b',
    'infrastructure_failure': r'\b(bridge|road|building|dam|power|outage|collapse|collapsed|closed)\b',
}
NEED_PATTERNS = {
    'rescue': r'\b(rescue|trapped|stranded|evacuate|evacuation)\b',
    'medical_assistance': r'\b(medical|ambulance|doctor|injur(?:y|ies)|hospital)\b',
    'fire_response': r'\b(firefighter|fire brigade|fire response)\b',
    'shelter': r'\b(shelter|evacuation centre|refuge)\b',
    'food': r'\b(food|hungry|meal)\b',
    'water': r'\b(water|thirst|drinking water)\b',
}
DATE_PATTERN = r'\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:today|yesterday|tomorrow|last night|this morning|on \w+ \d{1,2})\b'


def analyze_text(text: str) -> dict:
    normalized = ' '.join(text.split())
    lowered = normalized.casefold()
    incidents = [name for name, pattern in INCIDENT_PATTERNS.items() if re.search(pattern, lowered)]
    incident_type = incidents[0] if incidents else 'other_unknown'
    locations = []
    for match in re.finditer(r'\b(?:in|near|at|around|from)\s+([A-Za-z][\w.-]*(?:\s+[A-Za-z][\w.-]*){0,2})', normalized):
        candidate = match.group(1).rstrip(',.')
        candidate = re.split(r'\s+(?:needs?|reported|but|and)\b', candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if candidate and candidate.casefold() not in {item.casefold() for item in locations}:
            locations.append(candidate)
        for extra in re.findall(r'\band\s+([A-Za-z][\w.-]*)', match.group(1), flags=re.IGNORECASE):
            if extra.casefold() not in {item.casefold() for item in locations}:
                locations.append(extra.rstrip(',.'))
    location = locations[0] if locations else None
    severity = 'high' if re.search(r'\b(major|severe|critical|deadly|fatal|many injured|massive)\b', lowered) else ('moderate' if incidents else 'unknown')
    needs = [name for name, pattern in NEED_PATTERNS.items() if re.search(pattern, lowered)]
    temporal_clues = re.findall(DATE_PATTERN, lowered, flags=re.IGNORECASE)
    hypothetical = bool(re.search(r'\b(if|might|could|would|hypothetical|possible|alleged)\b', lowered))
    crisis_language = bool(incidents or needs or re.search(r'\b(emergency|disaster|crisis|alert)\b', lowered))
    temporal_status = 'clues_conflict_or_multiple' if len(temporal_clues) > 1 else ('relative_date_clue' if temporal_clues and re.search(r'\b(today|yesterday|tomorrow|last night|this morning)\b', lowered) else ('date_clue_present' if temporal_clues else 'unknown'))
    return {
        'is_crisis_language': crisis_language,
        'statement_type': 'hypothetical_or_uncertain' if hypothetical else 'reported_or_descriptive',
        'incident_type': incident_type,
        'location': location,
        'locations': locations,
        'severity': severity,
        'needs': needs or ['none_identified'],
        'supporting_text': normalized[:12000],
        'temporal_clues': temporal_clues,
        'currentness': temporal_status,
        'limitations': ['Rule-based extraction; not a trained or calibrated classifier.', 'Location, severity, needs, and dates are clues requiring evidence and human review.'],
    }
