import shutil
import uuid
from threading import BoundedSemaphore
from datetime import datetime

import psutil
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile

from . import db
from .config import settings
from .pipeline import process_audio, process_image, process_text, process_video
from .models import availability
from .schemas import AnalysisResult, HistoryItem, JobDetail, JobResponse, TextRequest, EvidenceInput
from .evidence import prepare_document
from .media import capabilities
from .security import RequestLimits
from starlette.middleware.trustedhost import TrustedHostMiddleware


app = FastAPI(title="CrisisSense", version=settings.version)
app.add_middleware(RequestLimits)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])
db.initialize()
processing_slot = BoundedSemaphore(1)


def records() -> list[dict]:
    return db.many("SELECT * FROM evidence_documents ORDER BY ingested_at DESC LIMIT 200")


def create_job(modality: str) -> str:
    job_id = str(uuid.uuid4())
    if not db.insert_job(job_id, modality, datetime.utcnow().isoformat()):
        raise HTTPException(429, 'Local processing queue is full. Try again after a job finishes.')
    return job_id


def run_job(job_id: str, modality: str, payload: object, suffix: str = "") -> None:
    with processing_slot:
        _run_job(job_id, modality, payload, suffix)


def _run_job(job_id: str, modality: str, payload: object, suffix: str = '') -> None:
    if not db.transition(job_id, 'queued', 'processing'):
        return
    try:
        if modality == "text": result = process_text(job_id, str(payload), records())
        elif modality == "image":
            image_data, claim = payload if isinstance(payload, tuple) else (payload, "")
            result = process_image(job_id, bytes(image_data), records(), str(claim))
        elif modality == "audio": result = process_audio(job_id, bytes(payload), suffix, records())
        else: result = process_video(job_id, bytes(payload), records())
        db.complete_job(job_id, result)
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else 'Processing failed. Check local model and decoder availability.'
        db.transition(job_id, 'processing', 'failed', message)


async def file_bytes(upload: UploadFile, limit: int) -> bytes:
    try:
        # Read directly from the already-open bounded upload stream.  This is
        # deterministic for Starlette's in-memory and spooled file variants,
        # including lightweight test fixtures that do not expose ``_rolled``.
        data = upload.file.read(limit + 1)
    finally:
        close = upload.file.close
        close()
    if not data: raise HTTPException(422, "An upload is required.")
    if len(data) > limit: raise HTTPException(413, "Upload exceeds the configured size limit.")
    return data


@app.get("/api/health")
def health() -> dict: return {"status": "ok", "version": settings.version}


@app.get("/api/ready")
def ready() -> dict: return {"ready": settings.database_path.parent.exists(), "database": str(settings.database_path.name)}


@app.get("/api/status")
def status() -> dict:
    disk = shutil.disk_usage(settings.root)
    memory = psutil.virtual_memory()
    caps = capabilities()
    return {"version": settings.version, "capabilities": caps, "models": {"asr": "local_vosk" if caps['asr'] else "unavailable", "visual": "local_cache_adapter"}, "tools": {"tesseract": bool(shutil.which("tesseract")), "ffmpeg": bool(shutil.which("ffmpeg")), 'video_decoder': caps['decoder'], 'source_fetch': 'bounded_public_html'}, "resources": {"disk_free_bytes": disk.free, "memory_available_bytes": memory.available}, "limits": {"image_bytes": settings.max_image_bytes, "audio_bytes": settings.max_audio_bytes, "video_bytes": settings.max_video_bytes, "audio_seconds": settings.max_audio_seconds, "video_seconds": settings.max_video_seconds, "video_frames": settings.max_video_frames}}


@app.get("/api/models")
def models() -> dict: return {"models": availability() + [{"id": "tesseract", "task": "optional OCR", "available": bool(shutil.which("tesseract")), "license": "Apache-2.0"}, {"id": "vosk-model-small-en-us-0.15", "task": "English speech transcription", "available": capabilities()['asr'], 'license':'Apache-2.0'}]}


@app.get("/api/config")
def config() -> dict: return {"evidence_retrieval": "local collection plus bounded public HTML URL fetch", "online_retrieval": "no search provider or API key configured; only user-supplied URLs are fetched", "retention": "uploads are processed in memory and not retained"}


@app.post("/api/verify/text", response_model=JobResponse, status_code=202)
def verify_text(request: TextRequest, background: BackgroundTasks) -> JobResponse:
    job_id = create_job("text"); background.add_task(run_job, job_id, "text", request.text); return JobResponse(job_id=job_id, status="queued")


async def verify_upload(modality: str, upload: UploadFile, background: BackgroundTasks, claim: str = "") -> JobResponse:
    limits = {"image": settings.max_image_bytes, "audio": settings.max_audio_bytes, "video": settings.max_video_bytes}
    mime = (upload.content_type or '').split(';')[0]
    if mime not in {'application/octet-stream', ''} and not mime.startswith(modality + '/'):
        await upload.close()
        raise HTTPException(415, 'Upload Content-Type does not match this input mode.')
    if len(claim) > 12000:
        await upload.close()
        raise HTTPException(422, 'Accompanying claim exceeds 12000 characters.')
    data = await file_bytes(upload, limits[modality])
    job_id = create_job(modality)
    suffix = (upload.filename or "").rsplit(".", 1)[-1]
    background.add_task(run_job, job_id, modality, (data, claim) if modality == "image" else data, f".{suffix}")
    return JobResponse(job_id=job_id, status="queued")


@app.post("/api/verify/image", response_model=JobResponse, status_code=202)
async def verify_image(background: BackgroundTasks, file: UploadFile = File(...), claim: str = Form("")) -> JobResponse: return await verify_upload("image", file, background, claim)

@app.post("/api/verify/audio", response_model=JobResponse, status_code=202)
async def verify_audio(background: BackgroundTasks, file: UploadFile = File(...)) -> JobResponse: return await verify_upload("audio", file, background)

@app.post("/api/verify/video", response_model=JobResponse, status_code=202)
async def verify_video(background: BackgroundTasks, file: UploadFile = File(...)) -> JobResponse: return await verify_upload("video", file, background)


@app.get("/api/jobs/{job_id}", response_model=JobDetail)
def job(job_id: str) -> JobDetail:
    value = db.one("SELECT * FROM jobs WHERE id=?", (job_id,))
    if not value: raise HTTPException(404, "Job not found.")
    result = AnalysisResult.model_validate_json(value["result_json"]) if value["result_json"] else None
    return JobDetail(job_id=value["id"], status=value["status"], stage=value["stage"], error=value["error"], result=result)


@app.post("/api/jobs/{job_id}/cancel", response_model=JobResponse)
def cancel(job_id: str) -> JobResponse:
    value = db.one("SELECT status FROM jobs WHERE id=?", (job_id,))
    if not value: raise HTTPException(404, "Job not found.")
    if value['status'] in {'queued', 'processing'}:
        db.transition(job_id, value['status'], 'cancelled')
    return JobResponse(job_id=job_id, status=db.one('SELECT status FROM jobs WHERE id=?', (job_id,))['status'])


@app.get("/api/history", response_model=list[HistoryItem])
def history() -> list[HistoryItem]: return [HistoryItem(analysis_id=x["id"], modality=x["modality"], verdict=x["verdict"], created_at=x["created_at"]) for x in db.many("SELECT id,modality,verdict,created_at FROM analyses ORDER BY created_at DESC")]


@app.get("/api/history/{analysis_id}", response_model=AnalysisResult)
def analysis(analysis_id: str) -> AnalysisResult:
    value = db.one("SELECT result_json FROM analyses WHERE id=?", (analysis_id,))
    if not value: raise HTTPException(404, "Analysis not found.")
    return AnalysisResult.model_validate_json(value["result_json"])


@app.delete("/api/history/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: str) -> None:
    db.delete_result(analysis_id)


@app.post('/api/evidence', status_code=201)
def add_evidence(value: EvidenceInput) -> dict:
    try:
        document = prepare_document(value, str(uuid.uuid4()))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    if db.one('SELECT count(*) AS n FROM evidence_documents')['n'] >= 200:
        raise HTTPException(409, 'Local evidence collection is limited to 200 documents.')
    columns = ','.join(document)
    placeholders = ','.join('?' for _ in document)
    db.execute(f'INSERT INTO evidence_documents ({columns}) VALUES ({placeholders})', tuple(document.values()))
    return {**document, 'retrieval_status': 'user_supplied_text; URL not fetched'}


@app.get('/api/evidence')
def evidence_collection() -> list[dict]:
    return records()


@app.delete('/api/evidence/{evidence_id}', status_code=204)
def delete_evidence(evidence_id: str) -> None:
    db.execute('DELETE FROM evidence_documents WHERE id=?', (evidence_id,))
