from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Verdict = Literal["SUPPORTED", "CONTRADICTED", "MIXED_EVIDENCE", "INSUFFICIENT_EVIDENCE"]
JobStatus = Literal["queued", "processing", "completed", "failed", "cancelled"]


class TextRequest(BaseModel):
    text: str = Field(min_length=3, max_length=12000)

    @field_validator('text')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError('Enter a claim with at least three non-space characters.')
        return value.strip()


class EvidenceInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default='', max_length=20000)
    publisher: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=2048)
    source_note: str = Field(min_length=3, max_length=1000)
    # A reviewer binds a relationship to one exact claim and a verbatim passage.
    reviewed_claim: str | None = Field(default=None, max_length=12000)
    relation: Literal['context', 'supports', 'contradicts'] = 'context'
    reviewer: str | None = Field(default=None, max_length=200)
    passage: str | None = Field(default=None, max_length=2000)

    @field_validator('title', 'body', 'source_note')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip() and value != '':
            raise ValueError('This field cannot be blank.')
        return value.strip()


class Claim(BaseModel):
    text: str
    modality: str
    source_location: str | None = None
    extraction_method: str
    extraction_confidence: float | None = None


class Evidence(BaseModel):
    evidence_id: str | None = None
    claim_text: str | None = None
    title: str
    publisher: str | None = None
    url: str | None = None
    excerpt: str
    category: Literal["official", "news", "fact_check", "user_provided", "unverified", "local"]
    relation: Literal["supports", "contradicts", "context", "insufficient"]
    retrieved_at: datetime | None = None
    published_at: datetime | str | None = None
    ingested_at: datetime | None = None
    source_note: str | None = None
    reviewer: str | None = None
    content_sha256: str | None = None
    retrieval_score: float | None = None
    status: str


class AnalysisResult(BaseModel):
    analysis_id: str
    modality: str
    verdict: Verdict
    confidence_type: str = "not_calibrated"
    explanation: str
    claims: list[Claim] = []
    supporting_evidence: list[Evidence] = []
    contradicting_evidence: list[Evidence] = []
    context_evidence: list[Evidence] = []
    observations: list[str] = []
    limitations: list[str] = []
    methods: list[str] = []
    processing_status: Literal['complete', 'partial'] = 'complete'
    stages: dict[str, str] = {}
    claim_assessments: list[dict] = []
    evidence_gaps: list[str] = []
    transcript: str | None = None
    transcript_words: list[dict] = []
    frames: list[dict] = []
    uncertainty: str = 'Uncalibrated; review source reliability and claim scope.'
    created_at: datetime


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobDetail(JobResponse):
    stage: str
    error: str | None = None
    result: AnalysisResult | None = None


class HistoryItem(BaseModel):
    analysis_id: str
    modality: str
    verdict: Verdict
    created_at: datetime
