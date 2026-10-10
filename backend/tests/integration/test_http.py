"""Real localhost HTTP against isolated SQLite, never the user's database."""
import io
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import wave

import httpx
import pytest
from PIL import Image


@pytest.fixture(scope='module')
def client(tmp_path_factory):
    root = Path(__file__).resolve().parents[3]
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    directory = tmp_path_factory.mktemp('http-integration')
    env = {**os.environ, 'CRISISSENSE_DB': str(directory/'test.sqlite'), 'HF_HUB_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1', 'OMP_NUM_THREADS':'2'}
    log = (directory/'server.log').open('w')
    process = subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',str(port)], cwd=root, env=env, stdout=log, stderr=log)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}', timeout=90) as http:
            for _ in range(100):
                try:
                    if http.get('/api/health').status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                if process.poll() is not None:
                    pytest.fail('Integration server exited; inspect test server.log')
                time.sleep(.1)
            else:
                pytest.fail('Integration server did not become healthy.')
            yield http
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
        log.close()


def await_job(client, response):
    assert response.status_code == 202, response.text
    identifier = response.json()['job_id']
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        job = client.get(f'/api/jobs/{identifier}').json()
        if job['status'] not in {'queued','processing'}:
            return job
        time.sleep(.05)
    pytest.fail('Job did not complete within 90 seconds.')


def test_evidence_to_verdict_history_and_delete(client):
    claim = 'The controlled test bridge is closed'
    ids = []
    for relation, expected in [('supports','SUPPORTED'), ('contradicts','MIXED_EVIDENCE')]:
        passage = 'The controlled test bridge is closed.' if relation == 'supports' else 'The controlled test bridge is open, not closed.'
        response = client.post('/api/evidence', json={'title':'Controlled test evidence', 'body':passage, 'source_note':'Synthetic integration fixture; not a real event', 'reviewed_claim':claim, 'relation':relation, 'reviewer':'Test', 'passage':passage})
        assert response.status_code == 201, response.text
        ids.append(response.json()['id'])
        result = await_job(client, client.post('/api/verify/text', json={'text':claim}))
        assert result['status'] == 'completed', result
        assert result['result']['verdict'] == expected
        assert client.get('/api/history/'+result['job_id']).json()['verdict'] == expected
    client.delete('/api/evidence/'+ids[0])
    result = await_job(client, client.post('/api/verify/text', json={'text':claim}))
    assert result['result']['verdict'] == 'CONTRADICTED'
    client.delete('/api/evidence/'+ids[1])
    result = await_job(client, client.post('/api/verify/text', json={'text':claim}))
    assert result['result']['verdict'] == 'INSUFFICIENT_EVIDENCE'
    assert client.delete('/api/history/'+result['job_id']).status_code == 204
    assert client.get('/api/jobs/'+result['job_id']).status_code == 404


def test_image_path_actual_features_and_persistence(client):
    buffer = io.BytesIO()
    Image.new('RGB',(32,32),(100,30,200)).save(buffer,'PNG')
    job = await_job(client, client.post('/api/verify/image', files={'file':('sample.png',buffer.getvalue(),'image/png')}, data={'claim':'The image shows a bridge.'}))
    assert job['status'] == 'completed', job
    assert job['result']['verdict'] == 'INSUFFICIENT_EVIDENCE'
    assert client.get('/api/history/'+job['job_id']).status_code == 200


def test_audio_path_processing_status(client):
    buffer = io.BytesIO()
    with wave.open(buffer,'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
        stream.writeframes(bytes(32000))
    job = await_job(client, client.post('/api/verify/audio', files={'file':('silence.wav',buffer.getvalue(),'audio/wav')}))
    assert job['status'] == 'completed', job
    assert job['result']['stages']['transcription'] in {'unavailable','complete'}
    assert job['result']['verdict'] == 'INSUFFICIENT_EVIDENCE'


def test_video_invalid_is_failed_and_service_survives(client):
    job = await_job(client, client.post('/api/verify/video',files={'file':('bad.mp4',b'not video','video/mp4')}))
    assert job['status'] == 'failed'
    assert client.get('/api/health').status_code == 200


def test_http_security_and_input_validation(client):
    assert client.post('/api/verify/text',json={'text':'   '}).status_code == 422
    assert client.post('/api/verify/text',json={'text':'a'*12001}).status_code == 422
    assert client.post('/api/verify/text',json={'text':'a claim'},headers={'Origin':'https://untrusted.example'}).status_code == 403
    assert client.post('/api/verify/image',files={'file':('x.png',b'bad','text/html')}).status_code == 415
    assert client.post('/api/evidence',json={'title':'bad','body':'bad','source_note':'bad','url':'http://127.0.0.1'}).status_code == 422
