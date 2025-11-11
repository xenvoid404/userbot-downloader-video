import asyncio
from pathlib import Path
from telethon import TelegramClient, events
from dotenv import load_dotenv

from src.config import Config
from src.logger import setup_logger
from src.task_manager import TaskManager
from src.handlers import CommandHandlers

load_dotenv()


class TelegramUserbot:
    """Main userbot application"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger()
        self.client = TelegramClient(config.SESSION, config.API_ID, config.API_HASH)
        self.task_manager = TaskManager(
            max_downloads=config.MAX_CONCURRENT_DOWNLOADS,
            max_uploads=config.MAX_CONCURRENT_UPLOADS,
            logger=self.logger,
        )
        self.handlers = CommandHandlers(
            self.client, self.task_manager, self.config, self.logger
        )
        self._register_handlers()

    def _register_handlers(self):
        """Register command handlers"""
        handlers = [
            (r"^/upload", self.handlers.handle_upload),
            (r"^/download", self.handlers.handle_download),
            (r"^/status", self.handlers.handle_status),
            (r"^/id", self.handlers.handle_id),
            (r"^/logs", self.handlers.handle_logs),
            (r"^/help", self.handlers.handle_help),
        ]

        for pattern, handler in handlers:
            self.client.on(events.NewMessage(outgoing=True, pattern=pattern))(handler)

    async def start(self):
        """Start the userbot"""
        self.logger.info("=" * 60)
        self.logger.info("🚀 TELEGRAM USERBOT STARTING")
        self.logger.info("=" * 60)

        await self.client.start()

        me = await self.client.get_me()
        self.logger.info(f"✅ Connected as: {me.first_name} (@{me.username or 'N/A'})")
        self.logger.info(f"📱 Phone: {me.phone or 'N/A'}")
        self.logger.info(f"📁 Download dir: {self.config.download_path}")
        self.logger.info(f"📤 Upload target: {self.config.GUDANG_CHAT_ID}")
        self.logger.info(
            f"⚙️ Max concurrent: Downloads={self.config.MAX_CONCURRENT_DOWNLOADS}, Uploads={self.config.MAX_CONCURRENT_UPLOADS}"
        )
        self.logger.info("=" * 60)
        self.logger.info("💡 Ready! Type /help for commands")
        self.logger.info("=" * 60)

        await self.client.run_until_disconnected()


async def main():
    """Application entry point"""
    try:
        config = Config()
        bot = TelegramUserbot(config)
        await bot.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
