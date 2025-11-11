import asyncio
from pathlib import Path
from typing import Optional


class FileManager:
    """Manages file operations"""

    @staticmethod
    async def cleanup_file(file_path: Path) -> bool:
        """Safely remove file asynchronously"""
        try:
            if file_path and file_path.exists():
                await asyncio.get_event_loop().run_in_executor(None, file_path.unlink)
                print(f"Cleaned up: {file_path.name}")  # Placeholder for logging
                return True
        except Exception as e:
            print(  # Placeholder for logging
                f"Cleanup failed for {file_path.name if file_path else 'unknown'}: {e}"
            )
        return False

    @staticmethod
    async def cleanup_files(*file_paths: Optional[Path]) -> None:
        """Cleanup multiple files"""
        tasks = [FileManager.cleanup_file(fp) for fp in file_paths if fp]
        await asyncio.gather(*tasks, return_exceptions=True)
