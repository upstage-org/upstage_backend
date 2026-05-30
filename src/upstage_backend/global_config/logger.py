"""Configures loguru; import ``logger`` from here (or re-exports) for all output — not the stdlib log package."""

from loguru import logger
import sys

logger.remove()

logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    colorize=sys.stdout.isatty(),
)

# logger.add(
#     "app.log",
#     rotation="10 MB",
#     retention="7 days",
#     format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
#     level="DEBUG"
# )
