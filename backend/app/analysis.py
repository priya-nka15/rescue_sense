"""Transparent, CPU-only crisis text analysis and entity extraction baselines.

Extracts incident type, location clues, severity indicators, resource needs, and temporal clues.
Clearly distinguishes extracted observations from independently verified facts.
"""
import re
from datetime import datetime, timezone

INCIDENT_PATTERNS = {
    'flood': r'\b(flood|flooding|flash flood|inundat\w*|waterlogged|heavy rain|torrential rain|overflowing)\b',
    'fire': r'\b(fire|wildfire|blaze|burning|smoke|explosion|engulfed|inferno)\b',
    'accident': r'\b(accident|collision|crash|crashed|wreck|derailment|pileup)\b',
    'earthquake': r'\b(earthquake|tremor|seismic|aftershock|tsunami)\b',
    'storm': r'\b(storm|cyclone|hurricane|typhoon|tornado|blizzard|gale)\b',
    'medical_emergency': r'\b(medical|ambulance|injur(?:y|ies)|hospital|heart attack|casualt(?:y|ies)|fatalit(?:y|ies))\b',
    'infrastructure_failure': r'\b(bridge|road|building|dam|power|outage|collapse|collapsed|closed|burst|structural failure)\b',
}

NEED_PATTERNS = {
    'rescue': r'\b(rescue|trapped|stranded|evacuate|evacuation|search and rescue|boats? needed)\b',
    'medical_assistance': r'\b(medical|ambulance|doctor|injur(?:y|ies)|hospital|first aid|paramedic)\b',
    'fire_response': r'\b(firefighter|fire brigade|fire response|fire engine)\b',
    'shelter': r'\b(shelter|evacuation centre|evacuation center|refuge|displaced)\b',
    'food': r'\b(food|hungry|meal|rations|supplies)\b',
    'water': r'\b(water|thirst|drinking water|clean water)\b',
    'power_and_utility': r'\b(generator|power outage|blackout|electricity|grid)\b',
}

DATE_PATTERN = (
    r'\b(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|'
    r'\b(?:\d{1,2}[-/]\d{1,2}[-/](?:19|20)?\d{2})\b|'
    r'\b(?:today|yesterday|tomorrow|last night|this morning|this afternoon|right now|currently)\b|'
    r'\b(?:on\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b|'
    r'\b(?:on\s+[A-Za-z]+\s+\d{1,2})\b'
)


def _extract_locations(text: str) -> list[str]:
    locations: list[str] = []
    for match in re.finditer(r'\b(?:in|near|at|around|from|across|along)\s+([A-Za-z][\w.-]*(?:\s+[A-Za-z][\w.-]*){0,2})', text):
        candidate = match.group(1).rstrip(',.')
        candidate = re.split(r'\s+(?:needs?|reported|but|and)\b', candidate, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if candidate and candidate.casefold() not in {item.casefold() for item in locations}:
            locations.append(candidate)
        for extra in re.findall(r'\band\s+([A-Za-z][\w.-]*)', match.group(1), flags=re.IGNORECASE):
            cleaned_extra = extra.rstrip(',.')
            if cleaned_extra and cleaned_extra.casefold() not in {item.casefold() for item in locations}:
                locations.append(cleaned_extra)
    return locations


def analyze_text(text: str) -> dict:
    """Analyze crisis text and extract structured situation indicators."""
    normalized = ' '.join(text.split())
    lowered = normalized.casefold()

    incidents = [name for name, pattern in INCIDENT_PATTERNS.items() if re.search(pattern, lowered)]
    incident_type = incidents[0] if incidents else 'other_unknown'

    locations = _extract_locations(normalized)
    location = locations[0] if locations else None

    # Severity assessment
    if re.search(r'\b(critical|catastrophic|multiple casualties|fatal|deadly|fatalities|mass casualty)\b', lowered):
        severity = 'high'
    elif re.search(r'\b(major|severe|massive|heavy damage|many injured|widespread)\b', lowered):
        severity = 'high'
    elif re.search(r'\b(minor|moderate|partial|small|isolated)\b', lowered):
        severity = 'moderate'
    else:
        severity = 'high' if (incidents and re.search(r'\b(rescue|emergency|urgent)\b', lowered)) else ('moderate' if incidents else 'unknown')

    needs = [name for name, pattern in NEED_PATTERNS.items() if re.search(pattern, lowered)]
    temporal_clues = re.findall(DATE_PATTERN, lowered, flags=re.IGNORECASE)
    hypothetical = bool(re.search(r'\b(if|might|could|would|hypothetical|possible|alleged|unconfirmed)\b', lowered))
    crisis_language = bool(incidents or needs or re.search(r'\b(emergency|disaster|crisis|alert|warning)\b', lowered))

    if len(temporal_clues) > 1:
        temporal_status = 'clues_conflict_or_multiple'
    elif temporal_clues and re.search(r'\b(today|yesterday|tomorrow|last night|this morning|right now|currently)\b', lowered):
        temporal_status = 'relative_date_clue'
    elif temporal_clues:
        temporal_status = 'date_clue_present'
    else:
        temporal_status = 'unknown'

    # Synthesize situation summary
    summary_parts = []
    if incident_type != 'other_unknown':
        summary_parts.append(f"{incident_type.replace('_', ' ').capitalize()} incident")
    if location:
        summary_parts.append(f"in/near {location}")
    if severity != 'unknown':
        summary_parts.append(f"assessed as {severity} severity")
    if needs:
        summary_parts.append(f"with reported needs for {', '.join(n.replace('_', ' ') for n in needs)}")
    situation_summary = " ".join(summary_parts) if summary_parts else "No specific crisis incident indicators identified."

    return {
        'is_crisis_language': crisis_language,
        'statement_type': 'hypothetical_or_uncertain' if hypothetical else 'reported_or_descriptive',
        'incident_type': incident_type,
        'incident_types': incidents,
        'location': location,
        'locations': locations,
        'severity': severity,
        'needs': needs or ['none_identified'],
        'supporting_text': normalized[:12000],
        'temporal_clues': temporal_clues,
        'currentness': temporal_status,
        'situation_summary': situation_summary,
        'observations_status': 'Extracted observations from input content; requires corroboration from independent sources.',
        'limitations': [
            'Rule-based clue extraction; not a trained or calibrated classifier.',
            'Location, severity, needs, and dates are clues requiring evidence and human review.',
        ],
    }
