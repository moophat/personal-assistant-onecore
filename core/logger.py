import logging
import sys
import os
from logging.handlers import RotatingFileHandler


class OneLineExceptionFormatter(logging.Formatter):
    """Format exceptions on a single line for cleaner logs."""

    def formatException(self, exc_info):
        result = super().formatException(exc_info)
        return repr(result)

    def format(self, record):
        result = super().format(record)
        if record.exc_text:
            result = result.replace("\n", " | ")
        return result


def init_logger(
    log_level=logging.INFO,
    log_file="logs/cli.log",
    file_size=2 * 1024 * 1024,
    file_count=2,
    shell_output=True,
    log_file_mode="a",
    log_format="%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s",
    print_log_init=False,
):
    """
    Initialize logger with rotating file handler and optional stdout output.

    Args:
        log_level: Logging level (default: INFO)
        log_file: Path to log file
        file_size: Max size per log file in bytes
        file_count: Number of backup files to keep
        shell_output: Whether to also output to stdout
        log_file_mode: File mode ('a' for append, 'w' for overwrite)
        log_format: Log message format string
        print_log_init: Whether to print initialization message

    Returns:
        Configured logger instance
    """
    try:
        main_logger = logging.getLogger()
        main_logger.setLevel(log_level)
        log_formatter = OneLineExceptionFormatter(log_format)

    except Exception as e:
        print(f"Exception when format logger: {e}")
        return None

    # Create log directory if needed
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        if print_log_init:
            print(f"Log directory: {log_dir}")

    try:
        # Clear existing handlers to prevent duplicates
        main_logger.handlers = []
        main_logger.propagate = False

        # Add rotating file handler
        log_rotate_handler = RotatingFileHandler(
            log_file,
            mode=log_file_mode,
            maxBytes=file_size,
            backupCount=file_count,
            encoding="utf-8",
            delay=0,
        )
        log_rotate_handler.setFormatter(log_formatter)
        log_rotate_handler.setLevel(log_level)
        main_logger.addHandler(log_rotate_handler)

    except Exception as e:
        print(f"Exception when creating file handler: {e}")

    try:
        # Add stdout handler if requested
        if shell_output:
            stream_log_handler = logging.StreamHandler(stream=sys.stdout)
            stream_log_handler.setFormatter(log_formatter)
            stream_log_handler.setLevel(log_level)
            main_logger.addHandler(stream_log_handler)

    except Exception as e:
        print(f"Exception when creating stdout handler: {e}")

    if print_log_init:
        print(f"Logging initialized: level={log_level}, file={os.path.abspath(log_file)}")

    return main_logger
