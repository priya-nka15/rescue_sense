"""Bounded local decoder subprocess; no upload paths or network inputs."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import signal

from .config import settings


def asr_path() -> Path:
    return Path(os.environ.get('CRISISSENSE_ASR_PATH', settings.root / 'data/models/vosk-model-small-en-us-0.15'))


def capabilities() -> dict:
    return {'decoder': importlib.util.find_spec('av') is not None or bool(decoder_tool('ffmpeg') and decoder_tool('ffprobe')),
            'asr': importlib.util.find_spec('vosk') is not None and (asr_path() / 'am/final.mdl').is_file(),
            'asr_model': 'vosk-model-small-en-us-0.15', 'language': 'en-US (configured, not detected)'}


def decoder_tool(name: str) -> str | None:
    installed = shutil.which(name)
    local = settings.root / 'data/tools/usr/bin' / name
    return installed or (str(local) if local.is_file() else None)


def decode(data: bytes, modality: str) -> dict:
    limit = settings.max_audio_bytes if modality == 'audio' else settings.max_video_bytes
    if not data or len(data) > limit:
        raise ValueError('Media upload is empty or exceeds its size limit.')
    if not capabilities()['decoder']:
        return {'status': 'unavailable', 'reason': 'No local decoder is installed.', 'frames': [], 'audio_status': 'unavailable'}
    env = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}
    env['LD_LIBRARY_PATH'] = str(settings.root / 'data/tools/usr/lib/x86_64-linux-gnu') + ':' + env.get('LD_LIBRARY_PATH', '')
    try:
        with tempfile.TemporaryDirectory(prefix='crisissense-media-') as temporary:
            with subprocess.Popen([sys.executable, '-m', 'backend.app.media_worker', modality, str(asr_path()), temporary],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  start_new_session=True, env=env, cwd=settings.root) as worker:
                try:
                    stdout, _ = worker.communicate(data, timeout=settings.media_timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid, signal.SIGKILL)
                    worker.communicate()
                    raise
                returncode = worker.returncode
    except subprocess.TimeoutExpired as error:
        raise ValueError('Media decoding/transcription exceeded the 60-second timeout.') from error
    if returncode:
        raise ValueError('Media decoder failed or exceeded its resource limit.')
    try:
        output = json.loads(stdout)
    except (ValueError, UnicodeError) as error:
        raise ValueError('Media decoder returned an invalid result.') from error
    if output.get('error'):
        raise ValueError(output['error'])
    return output
