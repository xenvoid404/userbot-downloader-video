import asyncio
import logging
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo

from src.config import Config
from src.utils import TaskType, create_progress_callback, humanbytes
from src.task_manager import TaskManager
from src.ffmpeg_helper import FFmpegHelper, FFmpegError
from src.file_manager import FileManager


class Workers:
    """Background workers for file operations"""

    @staticmethod
    async def download_worker(
        client: TelegramClient,
        event,
        message,
        filename: str,
        task_id: int,
        task_manager: TaskManager,
        config: Config,
        logger: logging.Logger,
    ) -> None:
        """
        Download file from Telegram with timeout and error handling

        Args:
            client: Telegram client
            event: Triggering event
            message: Message containing file to download
            filename: Target filename
            task_id: Unique task identifier
            task_manager: Task manager instance
            config: Application config
            logger: Logger instance
        """
        save_path = config.download_path / filename
        file_manager = FileManager(logger)

        async with task_manager.get_semaphore(TaskType.DOWNLOAD):
            try:
                file_size = message.file.size if message.file else 0
                logger.info(
                    f"Task {task_id:3} | DOWNLOAD | "
                    f"{filename} ({humanbytes(file_size)})"
                )

                # Download with progress and timeout
                await asyncio.wait_for(
                    client.download_media(
                        message,
                        file=str(save_path),
                        progress_callback=create_progress_callback(
                            filename,
                            "Downloading",
                            config.PROGRESS_UPDATE_INTERVAL,
                            logger,
                        ),
                    ),
                    timeout=config.DOWNLOAD_TIMEOUT,
                )

                logger.info(f"Task {task_id:3} | DOWNLOAD | Success: {filename}")

                await event.respond(
                    f"✅ **Download Complete** [`{task_id}`]\n"
                    f"📄 File: `{filename}`\n"
                    f"💾 Size: `{humanbytes(file_size)}`\n\n"
                    f"Upload: `/upload {filename} [caption]`"
                )

            except asyncio.TimeoutError:
                logger.error(f"Task {task_id:3} | DOWNLOAD | Timeout: {filename}")
                await event.respond(
                    f"❌ **Download Timeout** [`{task_id}`]\n`{filename}`"
                )
                await file_manager.cleanup_file(save_path)

            except Exception as e:
                logger.exception(f"Task {task_id:3} | DOWNLOAD | Error: {filename}")
                await event.respond(
                    f"❌ **Download Failed** [`{task_id}`]\nError: `{str(e)[:200]}`"
                )
                await file_manager.cleanup_file(save_path)

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
        logger: logging.Logger,
    ) -> None:
        """
        Upload file to Telegram with video optimization

        Args:
            client: Telegram client
            event: Triggering event
            filename: File to upload
            caption: Optional caption
            task_id: Unique task identifier
            task_manager: Task manager instance
            config: Application config
            logger: Logger instance
        """
        original_path = config.download_path / filename
        file_manager = FileManager(logger)
        ffmpeg = FFmpegHelper(logger)

        thumb_path: Optional[Path] = None
        optimized_path: Optional[Path] = None
        upload_path = original_path
        optimized = False

        async with task_manager.get_semaphore(TaskType.UPLOAD):
            try:
                if not original_path.exists():
                    raise FileNotFoundError(f"File not found: {filename}")

                logger.info(
                    f"Task {task_id:3} | UPLOAD   | "
                    f"{filename} | Caption: {caption or 'None'}"
                )

                # Video optimization
                if original_path.suffix.lower() in config.VIDEO_EXTENSIONS:
                    if await ffmpeg.check_if_video(original_path):
                        logger.info(
                            f"Task {task_id:3} | UPLOAD   | Optimizing video..."
                        )

                        optimized_path = await ffmpeg.optimize_for_streaming(
                            original_path
                        )

                        if optimized_path and optimized_path.exists():
                            upload_path = optimized_path
                            optimized = True
                            logger.info(
                                f"Task {task_id:3} | UPLOAD   | Using optimized file"
                            )
                        else:
                            logger.warning(
                                f"Task {task_id:3} | UPLOAD   | "
                                "Optimization failed, using original"
                            )

                # Extract metadata
                width, height, duration = await ffmpeg.get_video_metadata(upload_path)

                if not all([width, height, duration]):
                    raise ValueError("Failed to extract video metadata")

                # Generate thumbnail
                thumb_path = await ffmpeg.generate_thumbnail(
                    upload_path, config.THUMBNAIL_TIME, config.THUMBNAIL_QUALITY
                )

                # Prepare attributes
                attributes = [
                    DocumentAttributeVideo(
                        duration=duration,
                        w=width,
                        h=height,
                        supports_streaming=True,
                    )
                ]

                # Upload
                logger.info(
                    f"Task {task_id:3} | UPLOAD   | "
                    f"Uploading to {config.GUDANG_CHAT_ID}..."
                )

                await client.send_file(
                    config.GUDANG_CHAT_ID,
                    str(upload_path),
                    caption=caption,
                    thumb=str(thumb_path) if thumb_path else None,
                    attributes=attributes,
                    progress_callback=create_progress_callback(
                        filename, "Uploading", config.PROGRESS_UPDATE_INTERVAL, logger
                    ),
                )

                logger.info(f"Task {task_id:3} | UPLOAD   | Success: {filename}")

                await event.respond(
                    f"✅ **Upload Complete** [`{task_id}`]\n"
                    f"📄 File: `{filename}`\n"
                    f"📺 Resolution: `{width}x{height}`\n"
                    f"⏱️ Duration: `{duration}s`\n"
                    f"🎬 Streaming: `Enabled`\n"
                    f"🔧 Optimized: `{'Yes' if optimized else 'No'}`"
                )

            except FileNotFoundError as e:
                logger.error(f"Task {task_id:3} | UPLOAD   | {e}")
                await event.respond(
                    f"❌ **File Not Found** [`{task_id}`]\n`{filename}`"
                )

            except Exception as e:
                logger.exception(f"Task {task_id:3} | UPLOAD   | Error: {filename}")
                await event.respond(
                    f"❌ **Upload Failed** [`{task_id}`]\nError: `{str(e)[:200]}`"
                )

            finally:
                # Cleanup: thumbnail, optimized file, then original
                await file_manager.cleanup_files(
                    thumb_path,
                    optimized_path if optimized_path != original_path else None,
                    original_path,
                )
                await task_manager.remove_task(task_id)
