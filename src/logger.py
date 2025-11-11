import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with ANSI color codes"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        """Format log record with colors"""
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:8}{self.RESET}"
        return super().format(record)


def setup_logger(name: str = "userbot", level: int = logging.INFO) -> logging.Logger:
    """
    Setup application logger with colored output

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler with colored formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = ColoredFormatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Reduce telethon noise
    logging.getLogger("telethon").setLevel(logging.WARNING)

    return logger
