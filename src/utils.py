import time
import logging
from enum import Enum
from typing import Callable


class TaskType(Enum):
    """Task type enumeration"""

    DOWNLOAD = "download"
    UPLOAD = "upload"


def humanbytes(size: int) -> str:
    """
    Convert bytes to human-readable format

    Args:
        size: Size in bytes

    Returns:
        Human-readable string (e.g., "1.5 MB")
    """
    if not size:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    power = 1024
    index = 0

    while size >= power and index < len(units) - 1:
        size /= power
        index += 1

    return f"{size:.2f} {units[index]}"


def create_progress_callback(
    filename: str,
    action: str,
    interval: float,
    logger: logging.Logger,
) -> Callable[[int, int], None]:
    """
    Create throttled progress callback for file operations

    Args:
        filename: Name of file being processed
        action: Action being performed (e.g., "Downloading")
        interval: Minimum seconds between updates
        logger: Logger instance

    Returns:
        Progress callback function
    """
    last_update = {"time": 0.0}

    def callback(current: int, total: int) -> None:
        """Progress callback with throttling"""
        now = time.time()
        elapsed = now - last_update["time"]

        # Update on: interval passed, completion, or first call
        if elapsed >= interval or current == total or last_update["time"] == 0:
            percent = (current / total * 100) if total > 0 else 0
            logger.info(
                f"{action:12} | {filename:30} | "
                f"{humanbytes(current):>10}/{humanbytes(total):<10} ({percent:5.1f}%)"
            )
            last_update["time"] = now

    return callback
