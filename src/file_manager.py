import asyncio
import logging
from pathlib import Path
from typing import Optional, List


class FileManager:
    """Handles file operations with async support"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def cleanup_file(self, file_path: Optional[Path]) -> bool:
        """
        Safely remove a file

        Args:
            file_path: Path to file to remove

        Returns:
            True if file was removed, False otherwise
        """
        if not file_path or not file_path.exists():
            return False

        try:
            await asyncio.get_event_loop().run_in_executor(None, file_path.unlink)
            self.logger.debug(f"Cleaned up: {file_path.name}")
            return True
        except Exception as e:
            self.logger.error(f"Cleanup failed for {file_path.name}: {e}")
            return False

    async def cleanup_files(self, *file_paths: Optional[Path]) -> List[bool]:
        """
        Cleanup multiple files concurrently

        Args:
            *file_paths: Variable number of file paths to cleanup

        Returns:
            List of cleanup results (True/False for each file)
        """
        tasks = [self.cleanup_file(path) for path in file_paths if path is not None]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def ensure_directory(self, dir_path: Path) -> bool:
        """
        Ensure directory exists

        Args:
            dir_path: Directory path to create

        Returns:
            True if directory exists or was created
        """
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, dir_path.mkdir, True, True
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to create directory {dir_path}: {e}")
            return False

    def get_safe_filename(self, filename: str, extension: str = "") -> str:
        """
        Sanitize filename and ensure extension

        Args:
            filename: Original filename
            extension: Desired extension (with or without dot)

        Returns:
            Sanitized filename with correct extension
        """
        # Remove invalid characters
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")
        safe_name = safe_name.strip()

        # Ensure extension
        if extension:
            ext = extension if extension.startswith(".") else f".{extension}"
            if not safe_name.endswith(ext):
                safe_name = f"{safe_name}{ext}"

        return safe_name
