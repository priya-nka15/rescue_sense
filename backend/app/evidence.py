"""Bounded local/web retrieval and explicitly reviewer-scoped decisions."""
import hashlib
import ipaddress
import re
import socket
from html.parser import HTMLParser
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .models import embed_texts
from .schemas import Evidence, EvidenceInput

MAX_SOURCE_BYTES = 1_000_000
FETCH_TIMEOUT_SECONDS = 8


class _PageParser(HTMLParser):
    """Extract bounded human-readable text and common publication metadata."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: list[str] = []
        self.parts: list[str] = []
        self._in_title = False
        self._ignored = 0
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.casefold(): value or '' for key, value in attrs}
        if tag.casefold() == 'title':
            self._in_title = True
        if tag.casefold() in {'script', 'style', 'noscript', 'template', 'svg'}:
            self._ignored += 1
        if tag.casefold() == 'meta':
            key = attrs_map.get('name') or attrs_map.get('property') or attrs_map.get('itemprop')
            value = attrs_map.get('content')
            if key and value:
                self.meta[key.casefold()] = value.strip()[:300]

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == 'title':
            self._in_title = False
        if tag.casefold() in {'script', 'style', 'noscript', 'template', 'svg'} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored:
            return
        value = ' '.join(data.split())
        if not value:
            return
        if self._in_title:
            self.title.append(value)
        else:
            self.parts.append(value)


class _SafeRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_source_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def normalize(text: str) -> str:
    return ' '.join(text.casefold().split()).rstrip('.!?')


def validate_source_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower().rstrip('.')
    if parsed.scheme not in {'http', 'https'} or not host or parsed.username or parsed.password:
        raise ValueError('Source URL must be an HTTP(S) URL without credentials.')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host:
        raise ValueError('Internal source URLs are not accepted.')
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and not address.is_global:
        raise ValueError('Private, loopback, reserved and link-local URLs are not accepted.')
    try:
        if parsed.port not in {None, 80, 443}:
            raise ValueError('Only HTTP(S) standard ports are accepted.')
    except ValueError as error:
        raise ValueError('Invalid source URL port.') from error
    return url


def _public_dns(url: str) -> None:
    """Reject hosts resolving to private/reserved addresses before opening."""
    host = urlsplit(url).hostname
    if not host:
        raise ValueError('Source URL has no host.')
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as error:
        raise ValueError('Source host could not be resolved.') from error
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise ValueError('Source host resolves to a private or reserved address.')


def fetch_source(url: str) -> dict:
    """Fetch one public HTML page without following unsafe redirects or large bodies."""
    validate_source_url(url)
    _public_dns(url)
    request = Request(url, headers={'User-Agent': 'CrisisSense/0.1 evidence-reader', 'Accept': 'text/html,application/xhtml+xml'})
    try:
        with build_opener(_SafeRedirects()).open(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            validate_source_url(final_url)
            content_type = (response.headers.get('Content-Type') or '').casefold()
            if 'html' not in content_type and 'xml' not in content_type and content_type:
                raise ValueError('Source is not an HTML page.')
            length = response.headers.get('Content-Length')
            if length and int(length) > MAX_SOURCE_BYTES:
                raise ValueError('Source page exceeds the retrieval size limit.')
            payload = response.read(MAX_SOURCE_BYTES + 1)
            if len(payload) > MAX_SOURCE_BYTES:
                raise ValueError('Source page exceeds the retrieval size limit.')
            charset = response.headers.get_content_charset() or 'utf-8'
    except (HTTPError, URLError, TimeoutError, socket.timeout, ValueError) as error:
        raise ValueError(f'Source could not be retrieved: {error}') from error
    parser = _PageParser()
    try:
        parser.feed(payload.decode(charset, 'replace'))
    except (UnicodeError, ValueError) as error:
        raise ValueError('Source page could not be parsed as text.') from error
    body = ' '.join(parser.parts)
    if len(body) < 20:
        raise ValueError('Source page contained no usable text.')
    published = next((parser.meta.get(key) for key in ('article:published_time', 'datepublished', 'date', 'pubdate') if parser.meta.get(key)), None)
    return {'url': final_url, 'title': ' '.join(parser.title).strip()[:200] or final_url,
            'publisher': parser.meta.get('publisher') or parser.meta.get('og:site_name'),
            'published_at': published, 'body': body[:20000],
            'retrieved_at': datetime.now(timezone.utc).isoformat()}


def prepare_document(value: EvidenceInput, identifier: str) -> dict:
    url = validate_source_url(value.url)
    if not value.body.strip() and not url:
        raise ValueError('Evidence needs source text or a public source URL.')
    if value.relation != 'context':
        if not all(x and x.strip() for x in (value.reviewed_claim, value.reviewer, value.passage)):
            raise ValueError('A reviewed relationship requires an exact claim, reviewer and quoted passage.')
        if value.passage not in value.body:
            raise ValueError('The reviewed passage must occur verbatim in the evidence text.')
    return dict(id=identifier, title=value.title, body=value.body, publisher=value.publisher,
                url=url, category='user_provided', ingested_at=datetime.now(timezone.utc).isoformat(),
                source_note=value.source_note, reviewed_claim=value.reviewed_claim, relation=value.relation,
                reviewer=value.reviewer, passage=value.passage,
                content_sha256=hashlib.sha256(value.body.encode()).hexdigest())


def retrieve(claims, records: list[dict]):
    support, contradict, context, assessments = [], [], [], []
    methods = ['lexical_passage_retrieval', 'exact_claim_reviewer_relationship']
    gaps = []
    hydrated = []
    for original in records[:200]:
        record = dict(original)
        url = record.get('url')
        if url:
            try:
                fetched = fetch_source(url)
                methods.append('bounded_source_url_fetch')
                if record.get('relation') == 'context':
                    record.update({key: fetched[key] for key in ('title', 'publisher', 'body', 'published_at', 'retrieved_at')})
                    record['category'] = 'unverified'
                    record['source_note'] = 'Fetched public HTML source; not independently verified.'
                else:
                    # Keep the reviewer assertion intact and add fetched text as context.
                    hydrated.append({**record, 'id': f"{record['id']}:fetched", 'title': fetched['title'],
                                     'publisher': fetched['publisher'] or record.get('publisher'), 'body': fetched['body'],
                                     'relation': 'context', 'reviewed_claim': None, 'reviewer': None, 'passage': None,
                                     'category': 'unverified', 'source_note': 'Fetched public HTML source; reviewer assertion remains separate.',
                                     'retrieved_at': fetched['retrieved_at'], 'published_at': fetched['published_at']})
            except ValueError as error:
                gaps.append(f"Source unavailable for {url}: {error}")
        hydrated.append(record)
    records = hydrated
    # Cap both collection and passages; reviewers can manage the local collection.
    candidates = []
    for record in records[:200]:
        passages = [record.get('passage')] if record.get('passage') else []
        passages += [record['body'][start:start + 800] for start in range(0, min(len(record['body']), 4000), 800)]
        candidates.extend((record, passage) for passage in dict.fromkeys(passages) if passage)
    vectors = None
    if claims and candidates:
        try:
            vectors, _ = embed_texts([c.text for c in claims] + [p for _, p in candidates])
            methods.append('MiniLM_cosine_passage_ranking')
        except (RuntimeError, OSError, ValueError):
            gaps.append('Semantic retrieval unavailable; lexical retrieval was used.')
    for ci, claim in enumerate(claims):
        words = set(re.findall(r'\w+', claim.text.casefold()))
        ranked = []
        for index, (record, passage) in enumerate(candidates):
            tokens = set(re.findall(r'\w+', passage.casefold()))
            lexical = len(words & tokens) / max(1, len(words | tokens))
            semantic = sum(a*b for a, b in zip(vectors[ci], vectors[len(claims)+index])) if vectors else 0.0
            exact = normalize(record.get('reviewed_claim') or '') == normalize(claim.text)
            score = max(lexical, semantic)
            if exact or lexical >= .1 or semantic >= .45:
                ranked.append((exact, score, record, passage))
        ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
        seen, related = set(), []
        for exact, score, record, passage in ranked:
            if record['id'] in seen:
                continue
            seen.add(record['id'])
            relation = 'context'
            reviewed_passage = record.get('passage')
            if exact and record.get('reviewer') and reviewed_passage and reviewed_passage in record['body']:
                relation = record.get('relation') if record.get('relation') in {'supports', 'contradicts'} else 'context'
            retrieved_at = record.get('retrieved_at')
            item = Evidence(evidence_id=record['id'], claim_text=claim.text, title=record['title'],
                publisher=record.get('publisher'), url=record.get('url'), excerpt=reviewed_passage if relation != 'context' else passage,
                category=record['category'], relation=relation, retrieved_at=retrieved_at, published_at=record.get('published_at'), ingested_at=record.get('ingested_at'),
                source_note=record.get('source_note'), reviewer=record.get('reviewer'), content_sha256=record.get('content_sha256'),
                retrieval_score=round(score, 5), status='reviewer_assertion' if relation != 'context' else ('retrieved_context' if retrieved_at else 'local_passage_match'))
            {'supports': support, 'contradicts': contradict, 'context': context}[relation].append(item)
            related.append(relation)
            if len(seen) == 10:
                break
        verdict = decide('supports' in related, 'contradicts' in related)
        assessments.append({'claim': claim.text, 'verdict': verdict, 'basis': 'Exact-claim reviewer annotations; source reliability is not independently established.'})
        if verdict == 'INSUFFICIENT_EVIDENCE':
            gaps.append(f'No reviewed supporting or contradicting passage for: {claim.text}')
    if not claims:
        gaps.append('No checkable claim was extracted.')
    verdicts = [a['verdict'] for a in assessments]
    if 'MIXED_EVIDENCE' in verdicts or ('SUPPORTED' in verdicts and 'CONTRADICTED' in verdicts):
        verdict = 'MIXED_EVIDENCE'
    elif not verdicts or 'INSUFFICIENT_EVIDENCE' in verdicts:
        verdict = 'INSUFFICIENT_EVIDENCE'
    else:
        verdict = verdicts[0]
    return verdict, support, contradict, context, assessments, gaps, methods


def decide(support: bool, contradict: bool) -> str:
    return 'MIXED_EVIDENCE' if support and contradict else 'SUPPORTED' if support else 'CONTRADICTED' if contradict else 'INSUFFICIENT_EVIDENCE'
