"""Comprehensive tests for claim extraction, noisy speech transcripts, search providers,
per-claim verdicts, and evidence-based verification.
"""
from unittest.mock import Mock, patch
import pytest

from backend.app.claims import extract_claims
from backend.app.evidence import decide, prepare_document, retrieve
from backend.app.pipeline import process_text
from backend.app.schemas import EvidenceInput
from backend.app.search import DuckDuckGoProvider, SearchResult, get_search_provider


# ---------------------------------------------------------------------------
# 1. CLAIM EXTRACTION TESTS
# ---------------------------------------------------------------------------

def test_extract_claims_preserves_original_wording():
    text = "The river exceeded danger levels at 3pm. Four people were rescued near the bridge."
    claims = extract_claims(text, "text")
    assert len(claims) == 2
    assert claims[0].text == "The river exceeded danger levels at 3pm"
    assert claims[1].text == "Four people were rescued near the bridge"
    assert claims[0].extraction_confidence is not None
    assert claims[0].extraction_confidence >= 0.7


def test_extract_claims_rejects_questions_and_conversational_fillers():
    text = "Hello can you hear me? Is the dam broken? The dam has a visible crack on the left wall."
    claims = extract_claims(text, "text")
    assert len(claims) == 1
    assert "visible crack" in claims[0].text
    assert not any("?" in c.text for c in claims)
    assert not any("can you hear me" in c.text for c in claims)


def test_noisy_transcript_bridges_blows_is_rejected():
    # User-reported problem: "the bridges blows" should not be extracted as a claim
    noisy_fragment = "the bridges blows"
    claims = extract_claims(noisy_fragment, "video")
    assert len(claims) == 0, f"Expected 0 claims from noisy fragment, got: {[c.text for c in claims]}"


def test_noisy_transcript_retains_verifiable_proposition():
    transcript = "water rising on main street and two houses are submerged"
    claims = extract_claims(transcript, "audio")
    assert len(claims) >= 1
    # Original wording is preserved verbatim
    assert any("submerged" in c.text or "water rising" in c.text for c in claims)
    assert all(c.modality == "audio" for c in claims)


# ---------------------------------------------------------------------------
# 2. SEARCH PROVIDER TESTS
# ---------------------------------------------------------------------------

def test_search_provider_offline_graceful_degradation():
    with patch("backend.app.search.urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        provider = DuckDuckGoProvider()
        with pytest.raises(RuntimeError, match="DuckDuckGo search connection failed"):
            provider.search("flood in Bengaluru")


def test_search_provider_parses_duckduckgo_results():
    sample_html = """
    <html>
      <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fnews.example.com%2Fbridge-collapse&amp;rut=123">
        Official authorities confirmed the Riverdale bridge collapsed this morning.
      </a>
      <a class="result__url" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fnews.example.com%2Fbridge-collapse"></a>
    </html>
    """
    mock_resp = Mock()
    mock_resp.read.return_value = sample_html.encode("utf-8")
    mock_resp.__enter__ = Mock(return_value=mock_resp)
    mock_resp.__exit__ = Mock(return_value=False)

    with patch("backend.app.search.urllib.request.urlopen", return_value=mock_resp):
        provider = DuckDuckGoProvider()
        results = provider.search("Riverdale bridge collapse")
        assert len(results) == 1
        assert results[0].url == "https://news.example.com/bridge-collapse"
        assert "Riverdale bridge collapsed" in results[0].snippet


def test_get_search_provider_respects_offline_env():
    with patch.dict("os.environ", {"CRISISSENSE_SEARCH_PROVIDER": "disabled"}):
        provider, info = get_search_provider()
        assert provider is None
        assert info["provider"] == "disabled"
        assert info["status"] == "offline_mode"


# ---------------------------------------------------------------------------
# 3. PER-CLAIM VERDICTS & EVIDENCE EVALUATION TESTS
# ---------------------------------------------------------------------------

def _make_doc(relation, claim, identifier, body="The bridge is closed."):
    return prepare_document(
        EvidenceInput(
            title=f"Doc {identifier}",
            body=body,
            source_note="Test fixture",
            reviewed_claim=claim,
            relation=relation,
            reviewer="Analyst A",
            passage=body if relation != "context" else None,
        ),
        identifier,
    )


def test_per_claim_verdicts_evaluated_independently():
    # Claim 1: "The bridge is closed" -> supported
    # Claim 2: "The hospital is flooded" -> contradicted
    # Claim 3: "Three boats are arriving" -> unsupported
    doc_support = _make_doc("supports", "The bridge is closed", "doc-1", "The bridge is closed.")
    doc_contra = _make_doc("contradicts", "The hospital is flooded", "doc-2", "The hospital is flooded.")

    records = [doc_support, doc_contra]
    text = "The bridge is closed. The hospital is flooded. Three boats are arriving."
    result = process_text("job-multi", text, records)

    # Per-claim assessments
    assessments_by_claim = {a["claim"]: a["verdict"] for a in result.claim_assessments}
    assert assessments_by_claim.get("The bridge is closed") == "SUPPORTED"
    assert assessments_by_claim.get("The hospital is flooded") == "CONTRADICTED"
    assert assessments_by_claim.get("Three boats are arriving") == "INSUFFICIENT_EVIDENCE"

    # Overall aggregated verdict must reflect mixed/conflicting findings
    assert result.verdict == "MIXED_EVIDENCE"


def test_conflicting_evidence_on_single_claim():
    # One source says supports, another contradicts
    doc_support = _make_doc("supports", "The bridge is closed", "doc-s", "The bridge is closed.")
    doc_contra = _make_doc("contradicts", "The bridge is closed", "doc-c", "The bridge is closed.")

    result = process_text("job-conflict", "The bridge is closed.", [doc_support, doc_contra])
    assert result.verdict == "MIXED_EVIDENCE"
    assert len(result.supporting_evidence) >= 1
    assert len(result.contradicting_evidence) >= 1


def test_unsupported_claim_has_insufficient_evidence_and_gap():
    result = process_text("job-none", "An unprecedented meteor fell on Central Park.", [])
    assert result.verdict == "INSUFFICIENT_EVIDENCE"
    assert len(result.supporting_evidence) == 0
    assert len(result.contradicting_evidence) == 0
    assert any("No reviewed supporting or contradicting passage" in gap for gap in result.evidence_gaps)
