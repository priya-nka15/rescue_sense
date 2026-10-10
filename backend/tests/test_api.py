from backend.app import db
from backend.app.main import app, run_job
from backend.app.models import availability
import io
import wave

import pytest

from backend.app.pipeline import extract_claims, mp4_metadata, process_audio, process_video, sample_timestamps, wav_metadata


def configure_db(tmp_path, monkeypatch):
    monkeypatch.setenv("CRISISSENSE_DB", str(tmp_path / "test.db"))
    db.initialize()


def test_routes_and_text_job(tmp_path, monkeypatch):
    configure_db(tmp_path, monkeypatch)
    paths = {route.path for route in app.routes}
    assert {"/api/health", "/api/verify/text", "/api/verify/image", "/api/verify/audio", "/api/verify/video", "/api/history"} <= paths
    job_id = "text-job"
    db.execute("INSERT INTO jobs (id,status,stage,modality,created_at) VALUES (?,?,?,?,?)", (job_id, "queued", "queued", "text", "now"))
    run_job(job_id, "text", "A bridge has collapsed near the river.")
    job = db.one("SELECT status,result_json FROM jobs WHERE id=?", (job_id,))
    assert job["status"] == "completed"
    assert "INSUFFICIENT_EVIDENCE" in job["result_json"]


def test_invalid_image_and_invalid_video_fail(tmp_path, monkeypatch):
    configure_db(tmp_path, monkeypatch)
    for job_id, modality, payload in [("bad-image", "image", b"not-an-image"), ("bad-video", "video", b"not-a-video")]:
        db.execute("INSERT INTO jobs (id,status,stage,modality,created_at) VALUES (?,?,?,?,?)", (job_id, "queued", "queued", modality, "now"))
        run_job(job_id, modality, payload)
        assert db.one("SELECT status FROM jobs WHERE id=?", (job_id,))["status"] == "failed"


def test_audio_is_processed_without_a_model(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.app.pipeline.capabilities', lambda: {'decoder':False})
    configure_db(tmp_path, monkeypatch)
    db.execute("INSERT INTO jobs (id,status,stage,modality,created_at) VALUES (?,?,?,?,?)", ("audio-job", "queued", "queued", "audio", "now"))
    run_job("audio-job", "audio", b"ID3audio-bytes", ".mp3")
    result = db.one("SELECT result_json FROM jobs WHERE id=?", ("audio-job",))["result_json"]
    assert "Speech transcription is unavailable" in result


def test_cancelled_job_is_not_completed(tmp_path, monkeypatch):
    configure_db(tmp_path, monkeypatch)
    db.execute("INSERT INTO jobs (id,status,stage,modality,created_at) VALUES (?,?,?,?,?)", ("cancelled-job", "cancelled", "cancelled", "text", "now"))
    run_job("cancelled-job", "text", "A report that should not run.")
    assert db.one("SELECT status FROM jobs WHERE id=?", ("cancelled-job",))["status"] == "cancelled"


def test_claim_preprocessing_and_optional_model_reporting():
    claims = extract_claims("The bridge collapsed yesterday. This sentence is too short.", "text")
    assert claims[0].text == "The bridge collapsed yesterday"
    models = availability()
    assert models[0]["id"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert isinstance(models[0]["available"], bool)


def wav_fixture(seconds: int = 1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\0\0" * 8000 * seconds)
    return output.getvalue()


def mp4_fixture(duration_ms: int) -> bytes:
    timescale = 1000
    mvhd_payload = b"\0\0\0\0" + b"\0" * 8 + timescale.to_bytes(4, "big") + duration_ms.to_bytes(4, "big")
    mvhd = (8 + len(mvhd_payload)).to_bytes(4, "big") + b"mvhd" + mvhd_payload
    moov = (8 + len(mvhd)).to_bytes(4, "big") + b"moov" + mvhd
    return (12).to_bytes(4, "big") + b"ftyp" + b"isom" + moov


def test_audio_metadata_and_transcription_unavailable_state(monkeypatch):
    monkeypatch.setattr('backend.app.pipeline.capabilities', lambda: {'decoder':False})
    data = wav_fixture()
    assert wav_metadata(data)["duration_ms"] == 1000
    result = process_audio("audio", data, ".wav", [])
    assert "8000 Hz" in " ".join(result.observations)
    assert "transcription is unavailable" in " ".join(result.observations).lower()


def test_video_metadata_duration_limit_and_sampling_plan(monkeypatch):
    monkeypatch.setattr('backend.app.pipeline.capabilities', lambda: {'decoder':False})
    data = mp4_fixture(4_000)
    assert mp4_metadata(data)["duration_ms"] == 4000
    assert sample_timestamps(4000, 3) == [0, 2000, 3999]
    result = process_video("video", data, [])
    assert "representative frame timestamp" in " ".join(result.observations)
    assert "not available" in " ".join(result.observations)
    with pytest.raises(ValueError, match="duration"):
        process_video("long-video", mp4_fixture(181_000), [])


def test_video_job_completes_with_an_honest_unavailable_extraction_state(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.app.pipeline.capabilities', lambda: {'decoder':False})
    configure_db(tmp_path, monkeypatch)
    db.execute("INSERT INTO jobs (id,status,stage,modality,created_at) VALUES (?,?,?,?,?)", ("video-job", "queued", "queued", "video", "now"))
    run_job("video-job", "video", mp4_fixture(4_000))
    job = db.one("SELECT status,result_json FROM jobs WHERE id=?", ("video-job",))
    assert job["status"] == "completed"
    assert "FFmpeg is not available" in job["result_json"]
    assert "INSUFFICIENT_EVIDENCE" in job["result_json"]
