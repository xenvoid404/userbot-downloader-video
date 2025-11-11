import asyncio
import logging
from telethon import TelegramClient, events
from dotenv import load_dotenv

from src.config import Config
from src.logging_config import setup_logging
from src.task_manager import TaskManager
from src.handlers import CommandHandlers

load_dotenv()


class TelegramUserbot:
    """Main userbot class"""

    def __init__(self, config: Config):
        self.config = config
        self.client = TelegramClient(config.SESSION, config.API_ID, config.API_HASH)
        self.task_manager = TaskManager(
            max_downloads=config.MAX_CONCURRENT_DOWNLOADS,
            max_uploads=config.MAX_CONCURRENT_UPLOADS,
        )
        self.handlers = CommandHandlers(self.client, self.task_manager, self.config)
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup event handlers"""
        self.client.on(events.NewMessage(outgoing=True, pattern=r"^/upload"))(
            self.handlers.handle_upload
        )
        self.client.on(events.NewMessage(outgoing=True, pattern=r"^/download"))(
            self.handlers.handle_download
        )
        self.client.on(events.NewMessage(outgoing=True, pattern=r"^/status"))(
            self.handlers.handle_status
        )
        self.client.on(events.NewMessage(outgoing=True, pattern=r"^/id"))(
            self.handlers.handle_id
        )
        self.client.on(events.NewMessage(outgoing=True, pattern=r"^/logs"))(
            self.handlers.handle_logs
        )
        self.client.on(events.NewMessage(outgoing=True, pattern=r"^/help"))(
            self.handlers.handle_help
        )

    async def start(self):
        """Start the userbot"""
        log = setup_logging()
        log.info("=" * 60)
        log.info("🚀 TELEGRAM USERBOT STARTING")
        log.info("=" * 60)

        await self.client.start()

        me = await self.client.get_me()
        log.info(f"✅ Connected successfully!")
        log.info(f"👤 User: {me.first_name} (@{me.username or 'no username'})")
        log.info(f"📱 Phone: {me.phone or 'N/A'}")
        log.info(f"📁 Download dir: {self.config.download_path.absolute()}")
        log.info(f"📤 Upload target: {self.config.GUDANG_CHAT_ID}")
        log.info("=" * 60)
        log.info("💡 Bot ready! Type /help for commands")
        log.info("=" * 60)

        await self.client.run_until_disconnected()


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Main entry point"""
    config = Config()
    bot = TelegramUserbot(config)

    try:
        await bot.start()
    except KeyboardInterrupt:
        log = setup_logging()
        log.info("👋 Shutting down gracefully...")
    except Exception as e:
        log = setup_logging()
        log.exception(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
