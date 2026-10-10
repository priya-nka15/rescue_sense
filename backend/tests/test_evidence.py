from email.message import Message
import pytest
from backend.app.evidence import prepare_document, retrieve, validate_source_url
from backend.app.pipeline import extract_claims, process_text
from backend.app.schemas import EvidenceInput, TextRequest


@pytest.fixture(autouse=True)
def offline_features(monkeypatch):
    def unavailable(*args):
        raise RuntimeError('Unavailable for unit test')
    monkeypatch.setattr('backend.app.evidence.embed_texts', unavailable)


def document(relation='context', claim='The bridge is closed', identifier='source-1'):
    return prepare_document(EvidenceInput(title='Controlled fixture', body='The bridge is closed according to this test statement.',
        source_note='Synthetic unit fixture, not a real report', reviewed_claim=claim, relation=relation,
        reviewer='Test reviewer', passage='The bridge is closed'), identifier)


@pytest.mark.parametrize('relations,verdict', [([], 'INSUFFICIENT_EVIDENCE'), (['supports'],'SUPPORTED'), (['contradicts'],'CONTRADICTED'), (['supports','contradicts'],'MIXED_EVIDENCE'), (['context'],'INSUFFICIENT_EVIDENCE')])
def test_verdicts_preserve_reviewed_relationships(relations, verdict):
    records = [document(relation, identifier=str(i)) for i,relation in enumerate(relations)]
    result = process_text('test', 'The bridge is closed.', records)
    assert result.verdict == verdict
    for evidence in result.supporting_evidence + result.contradicting_evidence:
        assert evidence.excerpt == 'The bridge is closed'
        assert evidence.reviewer == 'Test reviewer'
        assert evidence.retrieved_at is None
        assert evidence.content_sha256


def test_similarity_and_unreviewed_exact_text_do_not_establish_truth(monkeypatch):
    monkeypatch.setattr('backend.app.evidence.embed_texts', lambda texts: ([[1.0]] * len(texts), 1))
    assert process_text('test', 'The bridge is closed.', [document()]).verdict == 'INSUFFICIENT_EVIDENCE'
    assert process_text('test', 'The bridge is open.', [document('supports')]).verdict == 'INSUFFICIENT_EVIDENCE'


def test_unresolved_second_claim_keeps_overall_abstention():
    result = process_text('test', 'The bridge is closed. The school is closed.', [document('supports')])
    assert result.verdict == 'INSUFFICIENT_EVIDENCE'
    assert result.supporting_evidence


def test_questions_and_uncertainty_are_not_rewritten():
    claims = extract_claims('Is the bridge closed? The bridge might be closed.', 'text')
    assert len(claims) == 1 and 'might' in claims[0].text


@pytest.mark.parametrize('url', ['file:///etc/passwd','http://127.0.0.1','http://169.254.169.254','http://[::1]','http://10.1.2.3','http://localhost','https://user:secret@example.com','https://example.com:444'])
def test_unsafe_source_urls_rejected(url):
    with pytest.raises(ValueError):
        validate_source_url(url)


def test_redirect_destination_is_dns_checked(monkeypatch):
    import backend.app.evidence as evidence
    from urllib.request import Request
    checked = []
    monkeypatch.setattr(evidence, '_public_dns', lambda url: checked.append(url))
    evidence._SafeRedirects().redirect_request(
        Request('https://example.com/start'), object(), 302, 'redirect', {}, 'https://example.com/next')
    assert checked == ['https://example.com/next']


def test_review_requires_verbatim_passage():
    value = EvidenceInput(title='Test', body='A valid document', source_note='Test', reviewed_claim='A claim', relation='supports', reviewer='Test', passage='Invented quotation')
    with pytest.raises(ValueError, match='verbatim'):
        prepare_document(value, '1')


def test_blank_text_rejected():
    with pytest.raises(ValueError):
        TextRequest(text='     ')


class FakeResponse:
    def __init__(self, body: bytes, url='https://example.com/report'):
        self._body = body
        self.headers = Message()
        self.headers['Content-Type'] = 'text/html; charset=utf-8'
        self._url = url
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self._url
    def read(self, limit=-1): return self._body[:limit]


def test_fetch_source_extracts_passages_and_metadata(monkeypatch):
    import backend.app.evidence as evidence
    monkeypatch.setattr(evidence, '_public_dns', lambda url: None)
    page = b'<html><head><title>Bridge update</title><meta property="og:site_name" content="Example News"><meta property="article:published_time" content="2026-01-02"></head><body><script>ignore()</script><p>The bridge is closed.</p><p>Use another road.</p></body></html>'
    monkeypatch.setattr(evidence, 'build_opener', lambda *args: type('Opener', (), {'open': lambda self, request, timeout: FakeResponse(page)})())
    result = evidence.fetch_source('https://example.com/report')
    assert result['title'] == 'Bridge update'
    assert result['publisher'] == 'Example News'
    assert 'The bridge is closed.' in result['body']
    assert 'ignore' not in result['body']
    assert result['published_at'] == '2026-01-02'


def test_fetched_unreviewed_source_is_context_only(monkeypatch):
    import backend.app.evidence as evidence
    monkeypatch.setattr(evidence, 'fetch_source', lambda url: {'url': url, 'title': 'Fetched report', 'publisher': 'Example', 'published_at': '2026-01-02', 'retrieved_at': '2026-01-03T00:00:00+00:00', 'body': 'The bridge is closed according to the report.'})
    record = prepare_document(EvidenceInput(title='URL source', body='', url='https://example.com/report', source_note='Public source'), 'url-1')
    result = process_text('test', 'The bridge is closed.', [record])
    assert result.verdict == 'INSUFFICIENT_EVIDENCE'
    assert result.context_evidence and result.context_evidence[0].status == 'retrieved_context'
    assert result.context_evidence[0].retrieved_at is not None
    assert not result.supporting_evidence and not result.contradicting_evidence


def test_inaccessible_source_is_reported_without_fabrication(monkeypatch):
    import backend.app.evidence as evidence
    monkeypatch.setattr(evidence, 'fetch_source', lambda url: (_ for _ in ()).throw(ValueError('Source could not be retrieved: timeout')))
    record = prepare_document(EvidenceInput(title='Unavailable URL', body='', url='https://example.com/report', source_note='Public source'), 'url-2')
    result = process_text('test', 'The bridge is closed.', [record])
    assert result.verdict == 'INSUFFICIENT_EVIDENCE'
    assert any('Source unavailable' in gap for gap in result.evidence_gaps)
    assert not result.supporting_evidence and not result.contradicting_evidence


def test_conflicting_review_survives_display_limit():
    records = [document('supports', identifier=str(i)) for i in range(12)]
    records.append(document('contradicts', identifier='opposing'))
    result = process_text('test', 'The bridge is closed.', records)
    assert result.verdict == 'MIXED_EVIDENCE'
    assert result.contradicting_evidence[0].evidence_id == 'opposing'


def test_fetched_provenance_and_late_passage(monkeypatch):
    import hashlib
    body = ('Navigation menu ' * 400) + ' The bridge is closed.'
    monkeypatch.setattr('backend.app.evidence.fetch_source', lambda url: dict(
        url='https://example.com/final', title='Final report', publisher=None,
        body=body, published_at=None, retrieved_at='2026-01-03T00:00:00+00:00'))
    record = prepare_document(EvidenceInput(title='Source', url='https://example.com/start',
                                           source_note='Test fixture'), 'source')
    result = process_text('test', 'The bridge is closed.', [record])
    assert result.verdict == 'INSUFFICIENT_EVIDENCE'
    item = result.context_evidence[0]
    assert 'The bridge is closed' in item.excerpt
    assert item.url == 'https://example.com/final'
    assert item.content_sha256 == hashlib.sha256(body.encode()).hexdigest()


def test_unknown_source_encoding_is_recoverable(monkeypatch):
    import backend.app.evidence as evidence
    response = FakeResponse(b'<p>Public source passage for review.</p>')
    response.headers.replace_header('Content-Type', 'text/html; charset=unknown-encoding')
    monkeypatch.setattr(evidence, '_public_dns', lambda url: None)
    monkeypatch.setattr(evidence, 'build_opener', lambda *args: type('Opener', (), {
        'open': lambda self, request, timeout: response})())
    with pytest.raises(ValueError, match='parsed as text'):
        evidence.fetch_source('https://example.com/report')
