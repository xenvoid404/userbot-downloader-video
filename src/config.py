import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class Config:
    """Application configuration with validation"""

    # Telegram API credentials
    API_ID: int = field(default_factory=lambda: int(os.getenv("API_ID", "0")))
    API_HASH: str = field(default_factory=lambda: os.getenv("API_HASH", ""))
    GUDANG_CHAT_ID: int = field(
        default_factory=lambda: int(os.getenv("GUDANG_CHAT_ID", "-100123456789"))
    )

    # Session and paths
    SESSION: str = "userbot_session"
    DOWNLOAD_DIR: str = "videos"

    # FFmpeg settings
    FFMPEG_TIMEOUT: int = 120
    THUMBNAIL_TIME: str = "00:00:05"
    THUMBNAIL_QUALITY: int = 3

    # Download/Upload settings
    DOWNLOAD_TIMEOUT: int = 3600
    PROGRESS_UPDATE_INTERVAL: float = 15.0

    # Concurrency limits
    MAX_CONCURRENT_DOWNLOADS: int = 3
    MAX_CONCURRENT_UPLOADS: int = 2

    # Supported formats
    VIDEO_EXTENSIONS: Tuple[str, ...] = (
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".flv",
        ".webm",
    )
    VIDEO_FORMATS: Tuple[str, ...] = ("mp4", "mov", "avi", "matroska", "webm", "flv")

    def __post_init__(self):
        """Validate configuration and create directories"""
        self._validate()
        self._setup_paths()

    def _validate(self):
        """Validate required configuration"""
        if not self.API_ID or self.API_ID == 0:
            raise ValueError("API_ID is required")
        if not self.API_HASH:
            raise ValueError("API_HASH is required")

    def _setup_paths(self):
        """Setup and create necessary directories"""
        self.download_path = Path(self.DOWNLOAD_DIR)
        self.download_path.mkdir(parents=True, exist_ok=True)
