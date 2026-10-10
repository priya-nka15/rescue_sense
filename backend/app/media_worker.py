"""Isolated, resource-limited PyAV/Vosk work. Input is bytes, never a URL."""
import base64
import io
import json
from pathlib import Path
import resource
import sys
import subprocess
import wave
import importlib.util
import audioop

from .config import settings


def recognize_wav(path: Path, model_path: str) -> dict:
    if not (Path(model_path) / 'am/final.mdl').is_file() or not importlib.util.find_spec('vosk'):
        return {'audio_status':'unavailable', 'transcript':None, 'words':[]}
    import vosk
    vosk.SetLogLevel(-1)
    with wave.open(str(path), 'rb') as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 16000:
            raise ValueError('Transcription requires 16 kHz mono 16-bit PCM audio.')
        if audio.getnframes() > settings.max_audio_seconds * 16000:
            raise ValueError('Audio duration exceeds the local processing limit.')
        has_signal = False
        while frames := audio.readframes(16000):
            if audioop.rms(frames, 2) > 0:
                has_signal = True
                break
        if not has_signal:
            return {'audio_status':'complete', 'transcript':'', 'words':[], 'reason':'no_speech'}
    recognizer = vosk.KaldiRecognizer(vosk.Model(model_path),16000)
    recognizer.SetWords(True)
    words, texts = [], []
    with wave.open(str(path), 'rb') as audio:
        while chunk := audio.readframes(4000):
            if recognizer.AcceptWaveform(chunk):
                item = json.loads(recognizer.Result())
                texts.append(item.get('text','')); words.extend(item.get('result', []))
    item = json.loads(recognizer.FinalResult())
    texts.append(item.get('text','')); words.extend(item.get('result', []))
    return {'audio_status':'complete', 'transcript':' '.join(filter(None,texts)), 'words':[{k:w[k] for k in ('word','start','end')} for w in words], 'language':'en-US (configured, not detected)'}


def ffmpeg_process(data: bytes, modality: str, model_path: str, directory: Path):
    from .media import decoder_tool
    path = directory/'input.media'
    path.write_bytes(data)
    ffmpeg, ffprobe = decoder_tool('ffmpeg'), decoder_tool('ffprobe')
    probe = subprocess.run([ffprobe, '-v','error','-protocol_whitelist','file,pipe','-format_whitelist','mov,wav,mp3,ogg', '-show_entries','format=duration:stream=index,codec_type,width,height,duration', '-of','json',str(path)], capture_output=True, check=False, timeout=10)
    if probe.returncode:
        raise ValueError('Media container could not be decoded.')
    metadata = json.loads(probe.stdout)
    duration = float(metadata.get('format',{}).get('duration',0))
    maximum = settings.max_video_seconds if modality == 'video' else settings.max_audio_seconds
    if not 0 < duration <= maximum:
        raise ValueError('Media duration is invalid, missing or exceeds the limit.')
    base = [ffmpeg, '-v','error','-nostdin','-y','-threads','1','-filter_threads','1','-max_alloc','134217728','-protocol_whitelist','file,pipe','-format_whitelist','mov,wav,mp3,ogg']
    frames = []
    if modality == 'video':
        videos = [s for s in metadata['streams'] if s['codec_type']=='video']
        if not videos:
            raise ValueError('Container has no video stream.')
        stream = videos[0]
        if stream['width']*stream['height'] > settings.max_image_pixels:
            raise ValueError('Video exceeds the pixel-count limit.')
        count = min(settings.max_video_frames,max(1,int(duration)))
        for index in range(count):
            target = index*duration/count
            destination = directory/f'frame-{index}.png'
            # showinfo supplies the decoded frame PTS; copyts preserves source timestamps.
            command = base + ['-loglevel','info','-copyts','-ss',str(target),'-i',str(path),'-map','0:v:0','-frames:v','1','-vf',"showinfo,scale=w='min(640,iw)':h='min(640,ih)':force_original_aspect_ratio=decrease",'-threads','1',str(destination)]
            extracted = subprocess.run(command,capture_output=True,timeout=10)
            if extracted.returncode or not destination.exists():
                raise ValueError('A sampled video frame could not be extracted.')
            import re
            timestamps = re.findall(rb'pts_time:([0-9.+-]+)',extracted.stderr)
            if not timestamps:
                raise ValueError('Decoder did not report a frame timestamp.')
            frames.append({'timestamp_ms':round(float(timestamps[0])*1000),'png':base64.b64encode(destination.read_bytes()).decode()})
    audio = {'audio_status':'no_audio', 'transcript':None,'words':[]}
    if any(s['codec_type']=='audio' for s in metadata['streams']):
        destination = directory/'audio.wav'
        extracted = subprocess.run(base+['-i',str(path),'-map','0:a:0','-vn','-ac','1','-ar','16000','-t',str(maximum+.1),'-c:a','pcm_s16le',str(destination)],capture_output=True,timeout=15)
        if extracted.returncode:
            audio['audio_status'] = 'failed'
        else:
            with wave.open(str(destination),'rb') as wav:
                if wav.getnframes()/wav.getframerate() > maximum:
                    raise ValueError('Decoded audio exceeds the duration limit.')
            audio = recognize_wav(destination,model_path)
    elif modality == 'audio':
        raise ValueError('Container has no audio stream.')
    return {'status':'complete','frames':frames,'duration_ms':round(duration*1000),'decoder':'FFmpeg',**audio}


def transcribe(data, model_path, max_seconds):
    import av
    with av.open(io.BytesIO(data)) as container:
        if not container.streams.audio:
            return {'audio_status': 'no_audio', 'transcript': None, 'words': []}
        stream = container.streams.audio[0]
        stream.codec_context.thread_count = 1
        if stream.duration and float(stream.duration * stream.time_base) > max_seconds:
            raise ValueError('Audio duration exceeds the local processing limit.')
        recognizer = None
        if (Path(model_path) / 'am/final.mdl').is_file():
            try:
                import vosk
                vosk.SetLogLevel(-1)
                recognizer = vosk.KaldiRecognizer(vosk.Model(model_path), 16000)
                recognizer.SetWords(True)
            except ImportError:
                pass
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        samples, segments, words = 0, [], []
        for frame in container.decode(stream):
            for pcm in resampler.resample(frame):
                samples += pcm.samples
                if samples > max_seconds * 16000:
                    raise ValueError('Decoded audio exceeds the duration limit.')
                if recognizer and recognizer.AcceptWaveform(pcm.to_ndarray().tobytes()):
                    segment = json.loads(recognizer.Result())
                    segments.append(segment.get('text', ''))
                    words.extend(segment.get('result', []))
        if not samples:
            raise ValueError('No audio samples could be decoded.')
        if recognizer:
            segment = json.loads(recognizer.FinalResult())
            segments.append(segment.get('text', ''))
            words.extend(segment.get('result', []))
        return {'audio_status': 'complete' if recognizer else 'unavailable',
                'duration_ms': round(samples / 16), 'transcript': ' '.join(filter(None, segments)) if recognizer else None,
                'words': [{k: w[k] for k in ('word', 'start', 'end')} for w in words][:5000],
                'language': 'en-US (configured, not detected)' if recognizer else None}


def process(data: bytes, modality: str, model_path: str) -> dict:
    if not importlib.util.find_spec('av'):
        return ffmpeg_process(data,modality,model_path,Path(sys.argv[3]))
    import av
    if modality == 'audio':
        return {'status': 'complete', 'frames': [], **transcribe(data, model_path, settings.max_audio_seconds)}
    with av.open(io.BytesIO(data)) as container:
        if not container.streams.video:
            raise ValueError('Container contains no decodable video stream.')
        stream = container.streams.video[0]
        stream.codec_context.thread_count = 1
        if stream.width * stream.height > settings.max_image_pixels:
            raise ValueError('Video resolution exceeds the pixel-count limit.')
        duration = float(stream.duration * stream.time_base) if stream.duration else (container.duration or 0) / av.time_base
        if duration <= 0 or duration > settings.max_video_seconds:
            raise ValueError('Video duration is missing, invalid or exceeds the limit.')
        count = min(settings.max_video_frames, max(1, int(duration)))
        frames, seen = [], set()
        # Seek to distributed targets and decode only a bounded GOP prefix per target.
        for index in range(count):
            target = index * duration / count
            origin = float((stream.start_time or 0) * stream.time_base)
            container.seek(int((target + origin) / stream.time_base), stream=stream, backward=True)
            for decoded, frame in enumerate(container.decode(stream)):
                if decoded >= 120:
                    break
                if frame.time is None or frame.time - origin + .001 < target:
                    continue
                if frame.width * frame.height > settings.max_image_pixels:
                    raise ValueError('Decoded frame exceeds the pixel-count limit.')
                timestamp = round((frame.time - origin) * 1000)
                if timestamp in seen:
                    break
                seen.add(timestamp)
                scale = min(1, settings.max_frame_dimension / max(frame.width, frame.height))
                image = frame.reformat(width=max(1, int(frame.width*scale)), height=max(1, int(frame.height*scale)), format='rgb24').to_image()
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                frames.append({'timestamp_ms': timestamp, 'png': base64.b64encode(buffer.getvalue()).decode()})
                break
        if not frames:
            raise ValueError('No frames were extracted within the sampling limits.')
    try:
        audio = transcribe(data, model_path, settings.max_video_seconds)
    except Exception:
        audio = {'audio_status': 'failed', 'transcript': None, 'words': []}
    return {'status': 'complete' if len(frames) == count else 'partial', 'frames': frames,
            'video_duration_ms': round(duration*1000), **audio}


if __name__ == '__main__':
    # Vosk's small model maps approximately 1.65 GiB of virtual address
    # space while using far less resident memory.  The previous 1.5 GiB cap
    # prevented model loading and made the parent hit its wall-time timeout.
    resource.setrlimit(resource.RLIMIT_AS, (2304*1024*1024, 2304*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (55, 55))
    resource.setrlimit(resource.RLIMIT_FSIZE, (64*1024*1024, 64*1024*1024))
    data = sys.stdin.buffer.read(settings.max_video_bytes + 1)
    try:
        if len(data) > settings.max_video_bytes:
            raise ValueError('Media exceeds the upload limit.')
        output = process(data, sys.argv[1], sys.argv[2])
    except ValueError as error:
        output = {'error': str(error)}
    except Exception:
        output = {'error': 'Media is corrupt, unsupported, or could not be decoded safely.'}
    print(json.dumps(output))
