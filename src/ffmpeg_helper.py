import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

from src.utils import humanbytes


class FFmpegError(Exception):
    """FFmpeg operation error"""

    pass


class FFmpegHelper:
    """Helper for FFmpeg operations"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def _run_command(
        self,
        command: list,
        description: str,
        timeout: int = 120,
    ) -> bytes:
        """
        Execute FFmpeg/ffprobe command

        Args:
            command: Command arguments list
            description: Operation description for logging
            timeout: Execution timeout in seconds

        Returns:
            Command stdout output

        Raises:
            FFmpegError: On execution failure
        """
        try:
            self.logger.debug(f"Executing: {' '.join(command)}")

            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise FFmpegError(f"{description} timeout after {timeout}s")

            if proc.returncode != 0:
                error = stderr.decode("utf-8", errors="ignore")[:500]
                raise FFmpegError(f"{description} failed: {error}")

            self.logger.debug(f"{description} completed")
            return stdout

        except FileNotFoundError:
            raise FFmpegError("FFmpeg not found. Please install FFmpeg.")
        except Exception as e:
            if not isinstance(e, FFmpegError):
                raise FFmpegError(f"{description} error: {e}")
            raise

    async def check_if_video(self, file_path: Path) -> bool:
        """
        Check if file is a video

        Args:
            file_path: Path to file

        Returns:
            True if file is a video format
        """
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(file_path),
        ]

        try:
            result = await self._run_command(command, f"Check {file_path.name}")
            data = json.loads(result.decode("utf-8"))
            format_name = data.get("format", {}).get("format_name", "").lower()

            video_formats = ["mp4", "mov", "avi", "matroska", "webm", "flv"]
            return any(fmt in format_name for fmt in video_formats)
        except Exception as e:
            self.logger.warning(f"Format check failed for {file_path.name}: {e}")
            return False

    async def get_video_metadata(
        self, file_path: Path
    ) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Extract video metadata

        Args:
            file_path: Path to video file

        Returns:
            Tuple of (width, height, duration) or (None, None, None) on error
        """
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(file_path),
        ]

        try:
            result = await self._run_command(command, f"Metadata {file_path.name}")
            data = json.loads(result.decode("utf-8"))

            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )

            if not video_stream:
                self.logger.warning(f"No video stream in {file_path.name}")
                return None, None, None

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            duration = int(float(video_stream.get("duration", 0)) + 0.5)

            self.logger.info(
                f"Metadata: {file_path.name} | {width}x{height} | {duration}s"
            )
            return width, height, duration

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            self.logger.error(f"Metadata parse failed for {file_path.name}: {e}")
            return None, None, None
        except FFmpegError as e:
            self.logger.error(f"Metadata extraction failed: {e}")
            return None, None, None

    async def generate_thumbnail(
        self, video_path: Path, time: str = "00:00:05", quality: int = 3
    ) -> Optional[Path]:
        """
        Generate video thumbnail

        Args:
            video_path: Path to video file
            time: Timestamp for thumbnail (HH:MM:SS format)
            quality: JPEG quality (2-31, lower is better)

        Returns:
            Path to generated thumbnail or None on failure
        """
        thumb_path = video_path.with_suffix(".jpg")

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            time,
            "-vframes",
            "1",
            "-q:v",
            str(quality),
            str(thumb_path),
        ]

        try:
            await self._run_command(command, f"Thumbnail {video_path.name}")

            if thumb_path.exists():
                size = thumb_path.stat().st_size
                self.logger.info(f"Thumbnail: {thumb_path.name} | {humanbytes(size)}")
                return thumb_path

            self.logger.warning(f"Thumbnail not created: {thumb_path.name}")
            return None

        except FFmpegError as e:
            self.logger.error(f"Thumbnail generation failed: {e}")
            return None

    async def optimize_for_streaming(
        self, input_path: Path, timeout: int = 180
    ) -> Optional[Path]:
        """
        Optimize video for streaming (faststart)

        Args:
            input_path: Path to input video
            timeout: Operation timeout

        Returns:
            Path to optimized file or None on failure
        """
        output_path = input_path.with_stem(f"{input_path.stem}_stream")

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
            str(output_path),
        ]

        try:
            await self._run_command(
                command, f"Optimize {input_path.name}", timeout=timeout
            )

            if output_path.exists():
                orig_size = input_path.stat().st_size
                opt_size = output_path.stat().st_size
                self.logger.info(
                    f"Optimized: {output_path.name} | "
                    f"{humanbytes(orig_size)} → {humanbytes(opt_size)}"
                )
                return output_path

            self.logger.warning(f"Optimization failed: no output file")
            return None

        except FFmpegError as e:
            self.logger.error(f"Optimization failed: {e}")
            return None
