from backend.app.analysis import analyze_text
from backend.app.pipeline import process_text


def test_incident_location_severity_and_needs_are_transparent():
    result = analyze_text('A major flood in Bengaluru needs rescue, shelter and water today.')
    assert result['incident_type'] == 'flood'
    assert result['location'] == 'Bengaluru'
    assert result['severity'] == 'high'
    assert {'rescue', 'shelter', 'water'} <= set(result['needs'])
    assert result['currentness'] == 'relative_date_clue'


def test_unknown_text_does_not_claim_crisis():
    result = analyze_text('The blue book is on the table.')
    assert result['incident_type'] == 'other_unknown'
    assert result['is_crisis_language'] is False
    assert result['severity'] == 'unknown'


def test_hypothetical_and_multiple_locations_remain_qualified():
    result = analyze_text('If there is a flood in Mumbai and Pune, rescue may be needed yesterday.')
    assert result['statement_type'] == 'hypothetical_or_uncertain'
    assert result['locations'] == ['Mumbai', 'Pune']
    assert result['currentness'] == 'relative_date_clue'


def test_text_result_contains_structured_member_analysis():
    result = process_text('x', 'A fire in Pune needs fire response.', [])
    assert result.crisis_analysis['incident_type'] == 'fire'
    assert result.crisis_analysis['location'] == 'Pune'
    assert result.currentness['status'] == 'unknown'
