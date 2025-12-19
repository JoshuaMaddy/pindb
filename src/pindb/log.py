import logging

from rich.logging import RichHandler

from pindb.config import CONFIGURATION


def setup_rich_logger():
    """Cycles through uvicorn root loggers to
    remove handler, then runs `get_logger_config()`
    to populate the `LoggerConfig` class with Rich
    logger parameters.
    """
    output_file_handler = logging.FileHandler(CONFIGURATION.log_file)

    handler_format = logging.Formatter(
        CONFIGURATION.logging_format,
        datefmt=CONFIGURATION.logging_date_format,
    )

    output_file_handler.setFormatter(handler_format)

    # Remove all handlers from root logger
    # and propagate to root logger.
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    logging.basicConfig(
        level=logging.INFO,
        format=CONFIGURATION.logging_format,
        datefmt=CONFIGURATION.logging_date_format,
        handlers=[
            RichHandler(
                rich_tracebacks=True, tracebacks_show_locals=True, show_time=False
            ),
            output_file_handler,
        ],
    )
