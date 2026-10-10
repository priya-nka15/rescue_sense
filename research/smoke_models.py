"""Bounded real local inference smoke tests; not benchmark evaluation."""
import argparse
import json
from pathlib import Path
import resource
from time import perf_counter

import psutil
from PIL import Image
from backend.app.models import embed_texts, image_features
from backend.app.pipeline import process_audio, process_video


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['text','image','audio','video'])
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    started = perf_counter()
    before = psutil.Process().memory_info().rss
    if args.mode == 'text':
        vectors, elapsed = embed_texts(['The bridge is closed.', 'The road is open.'])
        output = {'shape':[len(vectors),len(vectors[0])], 'adapter_ms':elapsed}
    elif args.mode == 'image':
        dimensions, elapsed = image_features(Image.new('RGB',(64,64),(30,80,120)))
        output = {'dimensions':dimensions,'adapter_ms':elapsed}
    else:
        if not args.fixture:
            parser.error('--fixture is required for audio/video')
        data = args.fixture.read_bytes()
        result = process_audio('smoke',data,args.fixture.suffix,[]) if args.mode == 'audio' else process_video('smoke',data,[])
        output = {'processing_status':result.processing_status,'stages':result.stages,'transcript':result.transcript,
                  'frame_timestamps_ms':[f['timestamp_ms'] for f in result.frames], 'verdict':result.verdict}
    output.update(mode=args.mode,device='cpu',elapsed_ms=round((perf_counter()-started)*1000),
                  rss_before_bytes=before,rss_after_bytes=psutil.Process().memory_info().rss,
                  process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    print(json.dumps(output, indent=2))
