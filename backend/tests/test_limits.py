import asyncio
import io
import subprocess
from unittest.mock import Mock, MagicMock

import pytest
from PIL import Image
from starlette.datastructures import UploadFile
from backend.app import db
from backend.app.main import file_bytes, run_job, cancel
from backend.app import pipeline
from backend.app.media import decode
from backend.app.security import RequestLimits


def test_upload_limit_closes_spooled_file():
    upload = UploadFile(io.BytesIO(b'123456'), filename='test.wav')
    with pytest.raises(Exception) as error:
        asyncio.run(file_bytes(upload, 3))
    assert error.value.status_code == 413
    assert upload.file.closed


def test_pixel_limit_precedes_feature_extraction(monkeypatch):
    buffer = io.BytesIO()
    Image.new('RGB', (20,20)).save(buffer, 'PNG')
    monkeypatch.setattr(pipeline, 'settings', Mock(max_image_bytes=100000, max_image_pixels=100))
    with pytest.raises(ValueError, match='pixel'):
        pipeline.process_image('image', buffer.getvalue(), [])


def test_ocr_failure_is_observation(monkeypatch):
    buffer = io.BytesIO()
    Image.new('RGB', (10,10)).save(buffer, 'PNG')
    monkeypatch.setattr(pipeline, 'image_features', lambda image: (576, 0))
    monkeypatch.setattr(pipeline.shutil, 'which', lambda name: '/fake/tesseract')
    monkeypatch.setattr(pipeline.subprocess, 'run', lambda *a,**kw: Mock(returncode=1, stdout=b'bad'))
    result = pipeline.process_image('image', buffer.getvalue(), [])
    assert result.verdict == 'INSUFFICIENT_EVIDENCE'
    assert 'OCR was unavailable or timed out.' in result.observations


def test_decoder_timeout_does_not_leak_paths(monkeypatch):
    monkeypatch.setattr('backend.app.media.capabilities', lambda: {'decoder': True})
    worker = MagicMock()
    worker.__enter__.return_value = worker
    worker.communicate.side_effect = [subprocess.TimeoutExpired('decoder',60), (b'',b'')]
    monkeypatch.setattr('backend.app.media.subprocess.Popen', lambda *a,**kw: worker)
    kill = Mock()
    monkeypatch.setattr('backend.app.media.os.killpg', kill)
    with pytest.raises(ValueError, match='timeout'):
        decode(b'fixture', 'audio')
    kill.assert_called_once()


def test_cancellation_survives_processing_error(tmp_path, monkeypatch):
    monkeypatch.setenv('CRISISSENSE_DB', str(tmp_path/'db.sqlite'))
    db.initialize()
    db.execute("INSERT INTO jobs(id,status,stage,modality,created_at) VALUES ('race','queued','queued','text','now')")
    def fail(*args):
        cancel('race')
        raise RuntimeError('/secret/internal/path')
    monkeypatch.setattr('backend.app.main.process_text', fail)
    run_job('race', 'text', 'fixture')
    assert db.one("SELECT status FROM jobs WHERE id='race'")['status'] == 'cancelled'
    assert not db.many('SELECT * FROM analyses')


def test_terminal_job_is_not_rerun(tmp_path, monkeypatch):
    monkeypatch.setenv('CRISISSENSE_DB', str(tmp_path/'db.sqlite'))
    db.initialize()
    db.execute("INSERT INTO jobs(id,status,stage,modality,created_at) VALUES ('done','completed','completed','text','now')")
    run_job('done', 'text', 'Should not run')
    assert cancel('done').status == 'completed'


def test_local_network_origins_are_allowed_but_public_origins_are_rejected():
    assert RequestLimits._allowed_origin('http://localhost:5173')
    assert RequestLimits._allowed_origin('http://192.168.1.25:5173')
    assert RequestLimits._allowed_origin('http://127.0.0.1:8000')
    assert not RequestLimits._allowed_origin('https://example.com:5173')
    assert RequestLimits._allowed_origin('http://192.168.1.25:9000')


def test_transcription_does_not_drop_speech_after_silent_intro(tmp_path, monkeypatch):
    import sys
    import wave
    from backend.app.media_worker import recognize_wav
    model = tmp_path / 'am'
    model.mkdir()
    (model / 'final.mdl').touch()
    audio = tmp_path / 'intro.wav'
    with wave.open(str(audio), 'wb') as stream:
        stream.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        stream.writeframes(bytes(96000) + b'\x01\x01' * 16000)
    recognizer = Mock()
    recognizer.AcceptWaveform.return_value = False
    recognizer.FinalResult.return_value = '{"text":"controlled mock speech"}'
    monkeypatch.setattr('importlib.util.find_spec', lambda name: True)
    monkeypatch.setitem(sys.modules, 'vosk', Mock(KaldiRecognizer=Mock(return_value=recognizer)))
    result = recognize_wav(audio, str(tmp_path))
    assert result['transcript'] == 'controlled mock speech'
    assert recognizer.AcceptWaveform.call_count > 0
