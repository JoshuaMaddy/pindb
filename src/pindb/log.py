"""Application logging: Rich console output, rotating file handler, user prefix."""

import logging
from logging.handlers import RotatingFileHandler
from typing import Any, MutableMapping

from rich.logging import RichHandler

from pindb.config import CONFIGURATION


class _UserLoggerAdapter(logging.LoggerAdapter):
    """Prefix every log record with ``[user=<id>]`` using the audit ContextVar.

    Resolved at emit time so the same adapter instance is safe to cache at
    module scope — each request fills the ContextVar via
    ``attach_user_middleware`` before any route code runs.
    """

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Prefix the message with the current audit user id from ContextVar state.

        Args:
            msg (Any): Original log message.
            kwargs (MutableMapping[str, Any]): Standard ``logging`` extras.

        Returns:
            tuple[Any, MutableMapping[str, Any]]: Message with ``[user=…]`` prefix
                and unchanged kwargs.

        Note:
            Imports ``get_audit_user`` lazily to avoid an import cycle with
            ``audit_events`` / ``config``.
        """
        # Local import avoids import cycle (audit_events imports config).
        from pindb.audit_events import get_audit_user

        user_id = get_audit_user()
        return f"[user={user_id if user_id is not None else '-'}] {msg}", kwargs


def user_logger(name: str) -> _UserLoggerAdapter:
    """Return a logger that prefixes each record with the current user id.

    Args:
        name (str): Logger name (typically ``__name__`` of the calling module).

    Returns:
        _UserLoggerAdapter: Adapter wrapping the stdlib logger *name*.
    """
    return _UserLoggerAdapter(logging.getLogger(name), {})


def setup_rich_logger() -> None:
    """Configure root logging with Rich (stderr) and a rotating log file.

    Clears handlers on existing named loggers so ``uvicorn`` reconfiguration
    picks up ``RichHandler`` plus ``RotatingFileHandler`` from ``CONFIGURATION``.
    """
    output_file_handler = RotatingFileHandler(
        filename=CONFIGURATION.log_file,
        maxBytes=CONFIGURATION.log_file_max_bytes,
        backupCount=CONFIGURATION.log_file_backup_count,
    )

    handler_format = logging.Formatter(
        fmt=CONFIGURATION.logging_format,
        datefmt=CONFIGURATION.logging_date_format,
    )

    output_file_handler.setFormatter(handler_format)

    # Remove all handlers from root logger
    # and propagate to root logger.
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers: list[logging.Handler] = []
        logging.getLogger(name).propagate = True

    logging.basicConfig(
        level=logging.INFO,
        format=CONFIGURATION.logging_format,
        datefmt=CONFIGURATION.logging_date_format,
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_time=False,
            ),
            output_file_handler,
        ],
    )
