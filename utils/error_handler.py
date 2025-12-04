import sys
import traceback
import logging
import asyncio

logger = logging.getLogger(__name__)

def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("-" * 80)
    logger.error("An error occurred:")
    logger.error("-" * 80)

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    for line in tb_lines:
        logger.error(line.rstrip())

    sys.exit(1)

sys.excepthook = handle_exception

def _asyncio_handler(loop, context):
    exc = context.get("exception")
    if exc is not None:
        handle_exception(type(exc), exc, exc.__traceback__)
        return
    logger.error("[asyncio error] %s", context.get("message", "unknown error"))

try:
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(_asyncio_handler)
except RuntimeError:
    pass