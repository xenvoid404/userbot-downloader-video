import logging


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and better structure"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname:8}{self.RESET}"
        return super().format(record)


def setup_logging() -> logging.Logger:
    """Setup logging with custom formatter"""
    logger = logging.getLogger("userbot")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Suppress telethon noise
    logging.getLogger("telethon").setLevel(logging.WARNING)

    return logger
