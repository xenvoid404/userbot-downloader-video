from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class Config:
    """Centralized configuration"""

    API_ID: int = os.getenv("API_ID")
    API_HASH: str = os.getenv("API_HASH")
    SESSION: str = "userbot_session"
    DOWNLOAD_DIR: str = "videos"
    GUDANG_CHAT_ID: int = os.getenv("GUDANG_CHAT_ID")

    # FFmpeg settings
    FFMPEG_TIMEOUT: int = 120
    THUMBNAIL_TIME: str = "00:00:05"
    THUMBNAIL_QUALITY: int = 3

    # Download settings
    DOWNLOAD_TIMEOUT: int = 3600
    PROGRESS_UPDATE_INTERVAL: float = 15.0

    # Task limits - Semaphore untuk membatasi concurrent tasks
    MAX_CONCURRENT_DOWNLOADS: int = 3
    MAX_CONCURRENT_UPLOADS: int = 2

    # Supported video extensions
    VIDEO_EXTENSIONS: tuple = (".mp4", ".mov", ".avi", ".mkv", ".flv", ".webm")

    def __post_init__(self):
        """Validate and create directories"""
        self.download_path = Path(self.DOWNLOAD_DIR)
        self.download_path.mkdir(exist_ok=True)
