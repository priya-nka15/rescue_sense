"""Extract a previously downloaded official Vosk archive with size/path bounds."""
import argparse
import hashlib
from pathlib import Path
import zipfile

MODEL = 'vosk-model-small-en-us-0.15'


def install(archive: Path, destination: Path):
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        if sum(entry.file_size for entry in entries) > 100*1024*1024:
            raise ValueError('Archive exceeds the 100 MiB expansion budget.')
        for entry in entries:
            path = Path(entry.filename)
            if path.is_absolute() or '..' in path.parts or path.parts[0] != MODEL:
                raise ValueError('Unexpected archive path.')
        if (destination / MODEL).exists():
            raise ValueError('Model already exists; refusing to overwrite it.')
        destination.mkdir(parents=True, exist_ok=True)
        source.extractall(destination)
    print({'model': MODEL, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
           'expanded_bytes': sum(entry.file_size for entry in entries)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path, default=Path('data/models'))
    args = parser.parse_args()
    install(args.archive, args.destination)
