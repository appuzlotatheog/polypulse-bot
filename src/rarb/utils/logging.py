"""Logging utilities for rarb."""

import logging
import sys
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

_console = Console()

def setup_logging(level: str = "INFO") -> None:
    """Set up structured logging with rich output."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=_console)],
    )

def get_logger(name: str) -> "LoggerProxy":
    """Get a proxy logger that supports key-value pairs."""
    return LoggerProxy(logging.getLogger(name))

class LoggerProxy:
    """Proxy for logging with extra context (like structlog)."""
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def _format_msg(self, msg: str, kwargs: Any) -> str:
        if not kwargs:
            return msg
        kv_str = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        return f"{msg} | {kv_str}"

    def info(self, msg: str, **kwargs: Any) -> None:
        self.logger.info(self._format_msg(msg, kwargs))

    def error(self, msg: str, **kwargs: Any) -> None:
        self.logger.error(self._format_msg(msg, kwargs))

    def debug(self, msg: str, **kwargs: Any) -> None:
        self.logger.debug(self._format_msg(msg, kwargs))

    def warning(self, msg: str, **kwargs: Any) -> None:
        self.logger.warning(self._format_msg(msg, kwargs))

def get_proxy_logger(name: str) -> LoggerProxy:
    """Get a proxy logger that supports key-value pairs."""
    return LoggerProxy(logging.getLogger(name))
