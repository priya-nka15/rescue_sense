from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    root: Path = Path(__file__).resolve().parents[2]
    max_image_bytes: int = 10 * 1024 * 1024
    max_audio_bytes: int = 25 * 1024 * 1024
    max_video_bytes: int = 50 * 1024 * 1024
    max_audio_seconds: int = 300
    max_video_seconds: int = 180
    max_video_frames: int = 12
    max_image_pixels: int = 12_000_000
    max_frame_dimension: int = 640
    media_timeout: int = 60
    version: str = "0.1.0"

    @property
    def database_path(self) -> Path:
        return Path(os.getenv("CRISISSENSE_DB", self.root / "data" / "crisissense.sqlite3"))


settings = Settings()
