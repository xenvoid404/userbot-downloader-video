import asyncio
from pathlib import Path
from typing import Optional
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from src.config import Config
from src.utils import create_progress_callback, humanbytes
from src.ffmpeg_helper import FFmpegHelper
from src.file_manager import FileManager
from src.task_manager import TaskManager, TaskType


class Workers:
    """Worker functions for download and upload operations"""

    @staticmethod
    async def download_worker(
        client: TelegramClient,
        event,
        message,
        filename: str,
        task_id: int,
        task_manager: TaskManager,
        config: Config,
    ) -> None:
        """Download worker with semaphore control"""
        from .logging_config import setup_logging

        log = setup_logging()

        save_path = config.download_path / filename

        # Acquire semaphore sebelum mulai download
        async with task_manager.download_semaphore:
            try:
                file_size = message.file.size if message.file else 0
                log.info(
                    f"Task {task_id:3} | DOWNLOAD | "
                    f"File: {filename} | Size: {humanbytes(file_size)}"
                )

                # Download with timeout protection
                download_task = client.download_media(
                    message,
                    file=str(save_path),
                    progress_callback=create_progress_callback(
                        filename, "Downloading", config.PROGRESS_UPDATE_INTERVAL
                    ),
                )

                await asyncio.wait_for(download_task, timeout=config.DOWNLOAD_TIMEOUT)

                log.info(f"Task {task_id:3} | DOWNLOAD | Success: {filename}")

                await event.respond(
                    f"✅ **Download Complete** [`{task_id}`]\n"
                    f"📄 File: `{filename}`\n"
                    f"💾 Size: `{humanbytes(file_size)}`\n\n"
                    f"Upload: `/upload {filename} [caption]`"
                )

            except asyncio.TimeoutError:
                from .utils import humanbytes

                log.error(f"Task {task_id:3} | DOWNLOAD | Timeout: {filename}")
                await event.respond(f"❌ **Timeout** [`{task_id}`]: `{filename}`")
                # Cleanup on failure
                await FileManager.cleanup_file(save_path)
            except Exception as e:
                from .utils import humanbytes

                log.exception(f"Task {task_id:3} | DOWNLOAD | Error: {filename}")
                await event.respond(
                    f"❌ **Download Failed** [`{task_id}`]\nError: `{str(e)[:200]}`"
                )
                # Cleanup on failure
                await FileManager.cleanup_file(save_path)
            finally:
                await task_manager.remove_task(task_id)

    @staticmethod
    async def upload_worker(
        client: TelegramClient,
        event,
        filename: str,
        caption: Optional[str],
        task_id: int,
        task_manager: TaskManager,
        config: Config,
    ) -> None:
        """Upload worker with video optimization and semaphore control"""
        from .logging_config import setup_logging
        from .utils import humanbytes

        log = setup_logging()

        original_file_path = config.download_path / filename
        thumb_path: Optional[Path] = None
        optimized_path: Optional[Path] = None
        upload_path: Path = original_file_path

        # Flag untuk track apakah optimized file dibuat
        optimization_successful = False

        # Acquire semaphore sebelum mulai upload
        async with task_manager.upload_semaphore:
            try:
                if not original_file_path.exists():
                    raise FileNotFoundError(f"File not found: {filename}")

                log.info(
                    f"Task {task_id:3} | UPLOAD   | "
                    f"File: {filename} | Caption: {caption or 'None'}"
                )

                # Check if video and optimize
                is_video_ext = (
                    original_file_path.suffix.lower() in config.VIDEO_EXTENSIONS
                )

                if is_video_ext:
                    is_video = await FFmpegHelper.check_if_video(original_file_path)

                    if is_video:
                        log.info(
                            f"Task {task_id:3} | UPLOAD   | Optimizing video for streaming..."
                        )
                        optimized_path = await FFmpegHelper.optimize_for_streaming(
                            original_file_path
                        )

                        # Hanya gunakan optimized file jika berhasil dibuat
                        if optimized_path and optimized_path.exists():
                            upload_path = optimized_path
                            optimization_successful = True
                            log.info(
                                f"Task {task_id:3} | UPLOAD   | Using optimized file"
                            )
                        else:
                            log.warning(
                                f"Task {task_id:3} | UPLOAD   | Optimization failed, using original file"
                            )
                            upload_path = original_file_path

                # Extract metadata from the file that will be uploaded
                width, height, duration = await FFmpegHelper.get_video_metadata(
                    upload_path
                )

                if not all([width, height, duration]):
                    raise ValueError("Failed to extract video metadata")

                # Generate thumbnail from the file that will be uploaded
                thumb_path = await FFmpegHelper.generate_thumbnail(upload_path)

                # Prepare video attributes
                attributes = [
                    DocumentAttributeVideo(
                        duration=duration, w=width, h=height, supports_streaming=True
                    )
                ]

                # Upload
                log.info(
                    f"Task {task_id:3} | UPLOAD   | Uploading to {config.GUDANG_CHAT_ID}..."
                )

                await client.send_file(
                    config.GUDANG_CHAT_ID,
                    str(upload_path),
                    caption=caption,
                    thumb=str(thumb_path) if thumb_path else None,
                    attributes=attributes,
                    progress_callback=create_progress_callback(
                        filename, "Uploading", config.PROGRESS_UPDATE_INTERVAL
                    ),
                )

                log.info(f"Task {task_id:3} | UPLOAD   | Success: {filename}")

                await event.respond(
                    f"✅ **Upload Complete** [`{task_id}`]\n"
                    f"📄 File: `{filename}`\n"
                    f"📺 Resolution: `{width}x{height}`\n"
                    f"⏱️ Duration: `{duration}s`\n"
                    f"🎬 Streaming: `Enabled`\n"
                    f"🔧 Optimized: `{'Yes' if optimization_successful else 'No'}`"
                )

            except Exception as e:
                log.exception(f"Task {task_id:3} | UPLOAD   | Error: {filename}")
                await event.respond(
                    f"❌ **Upload Failed** [`{task_id}`]\nError: `{str(e)[:200]}`"
                )
            finally:
                # Cleanup logic yang lebih jelas
                # Cleanup thumbnail (always)
                if thumb_path:
                    await FileManager.cleanup_file(thumb_path)

                # Cleanup optimized file (only if it was created and is different from original)
                if optimized_path and optimized_path != original_file_path:
                    await FileManager.cleanup_file(optimized_path)

                # Cleanup original file (always, after upload complete or failed)
                await FileManager.cleanup_file(original_file_path)

                await task_manager.remove_task(task_id)
