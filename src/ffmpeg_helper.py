import asyncio
import json
from pathlib import Path
from typing import Optional, Tuple


class FFmpegError(Exception):
    """Custom exception for FFmpeg operations"""

    pass


class FFmpegHelper:
    """Helper class for FFmpeg operations"""

    @staticmethod
    async def run_command(
        command: list,
        description: str,
        timeout: int = 120,  # Using Config.FFMPEG_TIMEOUT value
    ) -> Optional[bytes]:
        """Run FFmpeg/ffprobe command with proper error handling"""
        try:
            print(f"Running: {' '.join(command)}")  # Using print instead of log for now

            proc = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise FFmpegError(f"{description} timeout (>{timeout}s)")

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore")[:500]
                raise FFmpegError(f"{description} failed: {error_msg}")

            print(f"{description} completed successfully")
            return stdout

        except FileNotFoundError:
            raise FFmpegError("FFmpeg/ffprobe not found. Please install FFmpeg!")
        except Exception as e:
            raise FFmpegError(f"{description} error: {str(e)}")

    @staticmethod
    async def generate_thumbnail(video_path: Path) -> Optional[Path]:
        """Generate video thumbnail"""
        thumb_path = video_path.with_suffix(".jpg")

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            "00:00:05",  # Using Config.THUMBNAIL_TIME value
            "-vframes",
            "1",
            "-q:v",
            "3",  # Using Config.THUMBNAIL_QUALITY value
            str(thumb_path),
        ]

        try:
            await FFmpegHelper.run_command(
                command, f"Generate thumbnail for {video_path.name}"
            )

            if thumb_path.exists():
                from .utils import humanbytes

                print(  # Placeholder for logging
                    f"Thumbnail   | {thumb_path.name} | Size: {humanbytes(thumb_path.stat().st_size)}"
                )
                return thumb_path
        except FFmpegError as e:
            print(f"Thumbnail generation failed: {e}")

        return None

    @staticmethod
    async def get_video_metadata(
        file_path: Path,
    ) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Extract video metadata (width, height, duration)"""
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
            result = await FFmpegHelper.run_command(
                command, f"Extract metadata from {file_path.name}"
            )

            if not result:
                return None, None, None

            data = json.loads(result.decode("utf-8"))
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )

            if not video_stream:
                print("No video stream found in file")
                return None, None, None

            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            duration = int(float(video_stream.get("duration", 0)) + 0.5)

            print(  # Placeholder for logging
                f"Metadata    | Resolution: {width}x{height} | Duration: {duration}s"
            )
            return width, height, duration

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Failed to parse metadata: {e}")
            return None, None, None
        except FFmpegError as e:
            print(f"Metadata extraction failed: {e}")
            return None, None, None

    @staticmethod
    async def optimize_for_streaming(input_path: Path) -> Optional[Path]:
        """Optimize video for streaming with faststart flag

        Returns:
            Path ke file yang dioptimasi, atau None jika gagal
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
            await FFmpegHelper.run_command(
                command, f"Optimize {input_path.name} for streaming", timeout=180
            )

            if output_path.exists():
                original_size = input_path.stat().st_size
                optimized_size = output_path.stat().st_size

                print(  # Placeholder for logging
                    f"Optimized   | {output_path.name} | "
                    f"Original: {input_path.stat().st_size} → "
                    f"Optimized: {output_path.stat().st_size}"
                )
                return output_path
            else:
                print(f"Optimization failed: output file not created")
                return None

        except FFmpegError as e:
            print(f"Optimization failed: {e}")
            return None

    @staticmethod
    async def check_if_video(file_path: Path) -> bool:
        """Check if file is a video using ffprobe"""
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
            result = await FFmpegHelper.run_command(
                command, f"Check format of {file_path.name}"
            )

            if not result:
                return False

            data = json.loads(result.decode("utf-8"))
            format_name = data.get("format", {}).get("format_name", "").lower()

            video_formats = ["mp4", "mov", "avi", "matroska", "webm", "flv"]
            return any(fmt in format_name for fmt in video_formats)

        except Exception as e:
            print(f"Format check failed: {e}")
            return False
