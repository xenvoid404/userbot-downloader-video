import logging
from pathlib import Path
from typing import Optional
from telethon import TelegramClient, events
from src.config import Config
from src.utils import TaskType, humanbytes
from src.workers import Workers
from src.task_manager import TaskManager


class CommandHandlers:
    """Handle all command operations"""

    def __init__(
        self, client: TelegramClient, task_manager: TaskManager, config: Config
    ):
        self.client = client
        self.task_manager = task_manager
        self.config = config
        self.logger = logging.getLogger("userbot")

    async def handle_upload(self, event):
        """Handle /upload command"""
        if self.config.GUDANG_CHAT_ID == -100123456789:
            await event.edit("❌ Please set `GUDANG_CHAT_ID` in config!")
            return

        # Parse command
        parts = event.message.text.split(maxsplit=1)
        if len(parts) < 2:
            await event.edit(
                "❌ **Usage:**\n"
                "`/upload [filename] [caption]`\n\n"
                "**Example:**\n"
                "`/upload video.mp4`\n"
                "`/upload video.mp4 My awesome video`"
            )
            return

        args = parts[1].split(maxsplit=1)
        filename = args[0]
        caption = args[1] if len(args) > 1 else None

        file_path = self.config.download_path / filename
        if not file_path.exists():
            await event.edit(f"❌ File not found: `{filename}`")
            return

        # 1. Reserve task ID
        task_id = await self.task_manager.reserve_next_task_id()

        # 2. Create coroutine with correct ID
        coro = Workers.upload_worker(
            self.client,
            event,
            filename,
            caption,
            task_id,
            self.task_manager,
            self.config,
        )

        # 3. Register task (this starts execution)
        await self.task_manager.register_task(task_id, TaskType.UPLOAD, filename, coro)

        # Show semaphore status
        downloads = len(self.task_manager.get_tasks_by_type(TaskType.DOWNLOAD))
        uploads = len(self.task_manager.get_tasks_by_type(TaskType.UPLOAD))

        await event.edit(
            f"🚀 **Upload Queued** [`{task_id}`]\n"
            f"📄 File: `{filename}`\n"
            f"📊 Active: Downloads: `{downloads}/{self.config.MAX_CONCURRENT_DOWNLOADS}` | "
            f"Uploads: `{uploads}/{self.config.MAX_CONCURRENT_UPLOADS}`"
        )

    async def handle_download(self, event):
        """Handle /download command"""
        replied = await event.get_reply_message()
        if not replied or not replied.file:
            await event.edit("❌ Reply to a video/document file!")
            return

        # Parse command
        parts = event.message.text.split(maxsplit=1)
        if len(parts) < 2:
            await event.edit(
                "❌ **Usage:**\n`/download [filename]`\n\n`/download myvideo.mp4`"
            )
            return

        filename_base = parts[1].strip()

        # Auto extension
        ext = ".mp4"
        if replied.file.name and "." in replied.file.name:
            ext = "." + replied.file.name.rsplit(".", 1)[-1]
        elif replied.file.mime_type:
            ext = "." + replied.file.mime_type.split("/")[-1]

        filename = (
            filename_base if filename_base.endswith(ext) else f"{filename_base}{ext}"
        )

        # Check if file already exists
        file_path = self.config.download_path / filename
        if file_path.exists():
            await event.edit(
                f"⚠️ File `{filename}` already exists!\n"
                f"Delete it first or use a different name."
            )
            return

        # 1. Reserve task ID
        task_id = await self.task_manager.reserve_next_task_id()

        # 2. Create coroutine with correct ID
        coro = Workers.download_worker(
            self.client,
            event,
            replied,
            filename,
            task_id,
            self.task_manager,
            self.config,
        )

        # 3. Register task
        await self.task_manager.register_task(
            task_id, TaskType.DOWNLOAD, filename, coro
        )

        # Show semaphore status
        downloads = len(self.task_manager.get_tasks_by_type(TaskType.DOWNLOAD))
        uploads = len(self.task_manager.get_tasks_by_type(TaskType.UPLOAD))

        await event.edit(
            f"🚀 **Download Queued** [`{task_id}`]\n"
            f"📄 File: `{filename}`\n"
            f"💾 Size: `{humanbytes(replied.file.size)}`\n"
            f"📊 Active: Downloads: `{downloads}/{self.config.MAX_CONCURRENT_DOWNLOADS}` | "
            f"Uploads: `{uploads}/{self.config.MAX_CONCURRENT_UPLOADS}`"
        )

    async def handle_status(self, event):
        """Handle /status command"""
        tasks = self.task_manager.get_all_tasks()

        if not tasks:
            await event.edit("✅ No active tasks")
            return

        downloads = self.task_manager.get_tasks_by_type(TaskType.DOWNLOAD)
        uploads = self.task_manager.get_tasks_by_type(TaskType.UPLOAD)

        text = f"📊 **Active Tasks:** `{len(tasks)}`\n"
        text += f"⚙️ **Limits:** Downloads: `{self.config.MAX_CONCURRENT_DOWNLOADS}` | Uploads: `{self.config.MAX_CONCURRENT_UPLOADS}`\n\n"

        if downloads:
            text += f"⏬ **Downloads ({len(downloads)}):**\n"
            for task in downloads:
                text += f"  • [`{task.task_id}`] `{task.filename}`\n"
            text += "\n"

        if uploads:
            text += f"📤 **Uploads ({len(uploads)}):**\n"
            for task in uploads:
                text += f"  • [`{task.task_id}`] `{task.filename}`\n"

        await event.edit(text)

    async def handle_id(self, event):
        """Handle /id command"""
        chat_id = event.chat_id
        await event.edit(
            f"🆔 **Chat Information**\n\n"
            f"**ID:** `{chat_id}`\n"
            f"**Type:** `{'User' if chat_id > 0 else 'Group/Channel'}`"
        )

    async def handle_logs(self, event):
        """Handle /logs command"""
        current_level = self.logger.level

        if current_level == logging.INFO:
            self.logger.setLevel(logging.DEBUG)
            await event.edit("🔍 **Debug logging enabled**")
        else:
            self.logger.setLevel(logging.INFO)
            await event.edit("🔍 **Debug logging disabled**")

    async def handle_help(self, event):
        """Handle /help command"""
        help_text = f"""
🤖 **Telegram Userbot Commands**

**📥 Download:**
`/download [filename]` - Download replied video/file
Example: `/download myvideo.mp4`

**📤 Upload:**
`/upload [filename] [caption]` - Upload video with streaming optimization
Example: `/upload video.mp4 My Video Title`

**📊 Status:**
`/status` - Check active download/upload tasks

**🆔 Utilities:**
`/id` - Get current chat ID
`/logs` - Toggle debug logging
`/help` - Show this help message

**⚙️ Concurrency Limits:**
• Max concurrent downloads: `{self.config.MAX_CONCURRENT_DOWNLOADS}`
• Max concurrent uploads: `{self.config.MAX_CONCURRENT_UPLOADS}`

**Features:**
✅ Async operations with semaphore control
✅ Streaming optimization (automatic)
✅ Thumbnail generation
✅ Progress tracking
✅ Error recovery
✅ Automatic cleanup
"""
        await event.edit(help_text)
