import time
from enum import Enum
from typing import Callable


class TaskType(Enum):
    """Task types enumeration"""

    DOWNLOAD = "download"
    UPLOAD = "upload"


def humanbytes(size: int) -> str:
    """Convert bytes to human readable format"""
    if not size:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    power = 1024
    n = 0

    while size >= power and n < len(units) - 1:
        size /= power
        n += 1

    return f"{size:.2f} {units[n]}"


def create_progress_callback(
    filename: str, action: str = "Processing", progress_update_interval: float = 15.0
) -> Callable:
    """Factory for progress callback with throttling"""
    last_update = {"time": time.time()}

    def callback(current: int, total: int) -> None:
        now = time.time()
        if (now - last_update["time"] >= progress_update_interval) or (
            current == total
        ):
            pct = (current / total) * 100 if total > 0 else 0
            # Logging will be handled by the calling function
            print(  # This is placeholder - actual logging will be done by caller
                f"{action:12} | {filename:30} | "
                f"{humanbytes(current):>10}/{humanbytes(total):<10} ({pct:5.1f}%)"
            )
            last_update["time"] = now

    return callback
