import hashlib
import io
import shutil
import subprocess
import wave
import re
import warnings
import base64
from time import monotonic
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .config import settings
from .models import embed_texts, image_features
from .schemas import AnalysisResult, Claim, Evidence
from .evidence import retrieve
from .media import capabilities, decode
from .analysis import analyze_text


def now() -> datetime:
    return datetime.now(timezone.utc)


def wav_metadata(data: bytes) -> dict[str, int]:
    """Read safe WAV header metadata without writing a user file to disk."""
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            if rate <= 0:
                raise ValueError("The WAV file has an invalid sample rate.")
            return {"duration_ms": round(frames / rate * 1000), "sample_rate_hz": rate,
                    "channels": audio.getnchannels(), "sample_width_bytes": audio.getsampwidth()}
    except wave.Error as error:
        raise ValueError("The WAV file is malformed or unsupported.") from error


def mp4_metadata(data: bytes) -> dict[str, int | None]:
    """Parse only ISO-BMFF box headers and `mvhd`; this is not media decoding."""
    offset, duration_ms = 0, None
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], "big")
        box_type = data[offset + 4:offset + 8]
        if size == 0:
            size = len(data) - offset
        if size == 1:
            if offset + 16 > len(data):
                raise ValueError("The MP4 extended box header is truncated.")
            size = int.from_bytes(data[offset + 8:offset + 16], "big")
            header = 16
        else:
            header = 8
        if size < header or offset + size > len(data):
            raise ValueError("The MP4 box structure is malformed.")
        payload = data[offset + header:offset + size]
        if box_type == b"moov":
            child_offset = 0
            while child_offset + 8 <= len(payload):
                child_size = int.from_bytes(payload[child_offset:child_offset + 4], "big")
                child_type = payload[child_offset + 4:child_offset + 8]
                if child_size < 8 or child_offset + child_size > len(payload):
                    raise ValueError("The MP4 movie metadata is malformed.")
                if child_type == b"mvhd":
                    mvhd = payload[child_offset + 8:child_offset + child_size]
                    if len(mvhd) < 20:
                        raise ValueError("The MP4 movie header is truncated.")
                    version = mvhd[0]
                    if version == 0 and len(mvhd) >= 20:
                        timescale = int.from_bytes(mvhd[12:16], "big")
                        duration = int.from_bytes(mvhd[16:20], "big")
                    elif version == 1 and len(mvhd) >= 32:
                        timescale = int.from_bytes(mvhd[20:24], "big")
                        duration = int.from_bytes(mvhd[24:32], "big")
                    else:
                        raise ValueError("The MP4 movie-header version is unsupported.")
                    if timescale <= 0:
                        raise ValueError("The MP4 movie header has an invalid timescale.")
                    duration_ms = round(duration / timescale * 1000)
                child_offset += child_size
        offset += size
    return {"duration_ms": duration_ms}


def sample_timestamps(duration_ms: int, max_frames: int) -> list[int]:
    if duration_ms <= 0 or max_frames <= 0:
        return []
    count = min(max_frames, max(1, (duration_ms + 999) // 1000))
    if count == 1:
        return [0]
    return [round(index * (duration_ms - 1) / (count - 1)) for index in range(count)]


from .claims import extract_claims


def base_result(analysis_id: str, modality: str, claims: list[Claim], observations: list[str], methods: list[str], records: list[dict], source_text: str = '') -> AnalysisResult:
    verdict, support, contradict, context, assessments, gaps, retrieval_methods = retrieve(claims, records)
    analysis = analyze_text(source_text or ' '.join(c.text for c in claims))
    return AnalysisResult(
        analysis_id=analysis_id, modality=modality, verdict=verdict,
        explanation=("Available passages do not resolve every extracted claim." if verdict == 'INSUFFICIENT_EVIDENCE' else
                     "Verdict reflects explicit reviewer relationships for the exact claims in the local collection. It is conditional on those sources and annotations; source credibility has not been independently verified."),
        claims=claims, supporting_evidence=support, contradicting_evidence=contradict, context_evidence=context, observations=observations,
        claim_assessments=assessments, evidence_gaps=gaps,
        stages={'claim_extraction': 'complete' if claims else 'no_claims', 'evidence_retrieval': 'complete', 'comparison': 'reviewer_scoped'},
        limitations=["Confidence not calibrated.", "Similarity, transcription, and visual observations do not establish truth, location, time, or provenance."],
        methods=methods + retrieval_methods, created_at=now(),
        crisis_analysis=analysis,
        currentness={'status': analysis['currentness'], 'temporal_clues': analysis['temporal_clues'], 'basis': 'text/OCR/transcript clues only; source dates require verified evidence.'},
    )


def process_text(analysis_id: str, text: str, records: list[dict]) -> AnalysisResult:
    return base_result(analysis_id, "text", extract_claims(text, "text"), [], ["sentence_heuristic", "rule_based_crisis_analysis"], records, text)


def process_image(analysis_id: str, data: bytes, records: list[dict], accompanying_text: str = "") -> AnalysisResult:
    try:
        if len(data) > settings.max_image_bytes:
            raise ValueError('Image exceeds the upload size limit.')
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(data))
            if image.width * image.height > settings.max_image_pixels:
                raise ValueError('Image exceeds the pixel-count limit.')
            image.verify()
            image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
            image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("The uploaded image could not be decoded safely.") from error
    observations = [f"Validated {image.format or 'image'} image: {image.width} x {image.height} pixels.", f"SHA-256: {hashlib.sha256(data).hexdigest()[:16]}..."]
    methods = ["Pillow_safe_decode", "sha256_integrity_hash"]
    claims = extract_claims(accompanying_text, "image") if accompanying_text.strip() else []
    feature_status, ocr_status = 'unavailable', 'unavailable'
    if accompanying_text.strip():
        observations.append("A user-provided accompanying claim will be compared only with available evidence, not inferred from visual features.")
    try:
        feature_count, elapsed_ms = image_features(image)
        observations.append(f"Extracted {feature_count}-dimensional MobileNetV3 visual features in {elapsed_ms} ms. These features do not establish event identity, location, time, or authenticity.")
        methods.append("MobileNetV3-Small_visual_features")
        feature_status = 'complete'
    except RuntimeError as error:
        observations.append(f"Visual feature extraction unavailable: {error}")
    if shutil.which("tesseract"):
        try:
            process = subprocess.run(["tesseract", "stdin", "stdout", "--psm", "6"], input=data, capture_output=True, timeout=20, check=False)
            if process.returncode:
                raise OSError('OCR failed')
            ocr = process.stdout.decode("utf-8", "replace").strip()[:12000]
            ocr_status = 'complete' if ocr else 'no_text'
            if ocr:
                observations.append("OCR text was extracted for claim review.")
                methods.append("tesseract_ocr")
                claims.extend(extract_claims(ocr, "image"))
        except (subprocess.TimeoutExpired, OSError):
            ocr_status = 'failed'
            observations.append("OCR was unavailable or timed out.")
    ocr_text = ' '.join(c.text for c in claims if c.modality == 'image')
    result = base_result(analysis_id, "image", claims[:5], observations, methods, records, accompanying_text + ' ' + ocr_text)
    result.stages.update(image_decode='complete', visual_features=feature_status, ocr=ocr_status)
    result.processing_status = 'partial' if feature_status != 'complete' or ocr_status in {'unavailable','failed'} else 'complete'
    return result


def process_audio(analysis_id: str, data: bytes, suffix: str, records: list[dict]) -> AnalysisResult:
    if len(data) > settings.max_audio_bytes:
        raise ValueError('Audio exceeds the upload size limit.')
    if capabilities()['decoder']:
        if suffix.lower() not in {'.wav', '.mp3', '.m4a', '.ogg'}:
            raise ValueError('Supported audio formats are WAV, MP3, M4A, and OGG.')
        return process_decoded(analysis_id, data, 'audio', records)
    observations = [f"Inspected audio header ({len(data)} bytes); full decoding is unavailable."]
    if suffix.lower() not in {".wav", ".mp3", ".m4a", ".ogg"}:
        raise ValueError("Supported audio formats are WAV, MP3, M4A, and OGG.")
    if suffix.lower() == ".wav":
        metadata = wav_metadata(data)
        if metadata["duration_ms"] > settings.max_audio_seconds * 1000:
            raise ValueError("Audio duration exceeds the local processing limit.")
        observations.append(f"WAV metadata: {metadata['duration_ms'] / 1000:.1f} seconds, {metadata['sample_rate_hz']} Hz, {metadata['channels']} channel(s).")
    elif suffix.lower() == ".mp3" and not data.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")):
        raise ValueError("The MP3 file signature is invalid.")
    elif suffix.lower() == ".ogg" and not data.startswith(b"OggS"):
        raise ValueError("The OGG file signature is invalid.")
    elif suffix.lower() == ".m4a" and (len(data) < 12 or data[4:8] != b"ftyp"):
        raise ValueError("The M4A container signature is invalid.")
    observations.append("Speech transcription is unavailable: no approved local ASR runtime or weights are installed. A transcript, when available, would require separate evidence verification.")
    result = base_result(analysis_id, "audio", [], observations, ["audio_header_validation", "transcription_adapter_unavailable"], records)
    result.processing_status = 'partial'
    result.stages.update(decoding='unavailable', transcription='unavailable')
    return result


def process_video(analysis_id: str, data: bytes, records: list[dict]) -> AnalysisResult:
    if len(data) > settings.max_video_bytes:
        raise ValueError('Video exceeds the upload size limit.')
    if len(data) < 12 or data[4:8] != b"ftyp":
        raise ValueError("Only valid MP4 video containers are currently supported.")
    if capabilities()['decoder']:
        return process_decoded(analysis_id, data, 'video', records)
    metadata = mp4_metadata(data)
    observations = [f"Validated MP4 container ({len(data)} bytes)."]
    duration_ms = metadata["duration_ms"]
    if duration_ms is None:
        observations.append("MP4 duration metadata is unavailable; no frame extraction will be attempted.")
    else:
        if duration_ms > settings.max_video_seconds * 1000:
            raise ValueError("Video duration exceeds the local processing limit.")
        timestamps = sample_timestamps(duration_ms, settings.max_video_frames)
        observations.append(f"Planned at most {len(timestamps)} representative frame timestamp(s): {timestamps} ms. Frames remain derived video artifacts, not independent evidence.")
    if not shutil.which("ffmpeg"):
        observations.append("FFmpeg is not available, so planned frames, audio extraction, and transcription were not executed.")
        result = base_result(analysis_id, "video", [], observations, ["mp4_container_metadata", "frame_sampling_plan", "audio_transcription_adapter_unavailable"], records)
        result.processing_status = 'partial'
        result.stages.update(frame_extraction='unavailable', transcription='unavailable')
        return result
    observations.append("FFmpeg is available but bounded frame/audio extraction is not enabled in this release.")
    return base_result(analysis_id, "video", [], observations, ["mp4_container_metadata", "frame_sampling_plan"], records)


def process_decoded(analysis_id: str, data: bytes, modality: str, records: list[dict]) -> AnalysisResult:
    started = monotonic()
    decoded = decode(data, modality)
    transcript = decoded.get('transcript')
    claims = extract_claims(transcript or '', modality)
    observations = [f"Local {decoded.get('decoder','PyAV')} decoding: {decoded['status']}.", f"Speech processing: {decoded['audio_status']}."]
    if decoded.get('language'):
        observations.append(decoded['language'])
    if transcript == '':
        observations.append('No intelligible speech was recognized; this is not evidence of silence or truth.')
    methods, frames = [decoded.get('decoder','PyAV') + '_bounded_decoder'], []
    if decoded['audio_status'] == 'complete':
        methods.append('Vosk_small_en_us_0.15')
    partial = decoded['status'] != 'complete' or decoded['audio_status'] in {'unavailable', 'failed'}
    for frame in decoded.get('frames', []):
        if monotonic() - started > settings.media_timeout:
            partial = True
            observations.append('Frame interpretation stopped at the time budget.')
            break
        result = process_image(analysis_id, base64.b64decode(frame['png']), [])
        if result.processing_status == 'partial':
            partial = True
        timestamp = frame['timestamp_ms']
        frames.append({'timestamp_ms': timestamp, 'observations': result.observations, 'methods': result.methods})
        for claim in result.claims:
            claim.modality = 'video'
            claim.source_location = f'frame at {timestamp} ms'
            claims.append(claim)
    if modality == 'video':
        observations.append(f'Extracted {len(frames)} timestamped frames; derived frames and speech are observations, not independent corroboration.')
    result = base_result(analysis_id, modality, claims[:10], observations, methods, records, transcript or ' '.join(c.text for c in claims))
    result.processing_status = 'partial' if partial else 'complete'
    result.stages.update(decoding=decoded['status'], transcription=decoded['audio_status'])
    if modality == 'video':
        result.stages['frame_extraction'] = 'complete' if len(frames) == len(decoded.get('frames', [])) else 'partial'
    result.transcript, result.transcript_words, result.frames = transcript, decoded.get('words', []), frames
    return result
