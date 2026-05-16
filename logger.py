"""
logger.py – structured logging with loguru
"""
import sys
from pathlib import Path
from loguru import logger
from config import get_settings

settings = get_settings()

Path("./logs").mkdir(exist_ok=True)

logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> – {message}",
    colorize=True,
)
logger.add(
    settings.log_file,
    level="DEBUG",
    rotation="10 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} – {message}",
)

__all__ = ["logger"]
