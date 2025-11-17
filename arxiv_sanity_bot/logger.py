import json
import logging
import os
import sys
import warnings


class FatalError(Exception):
    """Exception raised for fatal errors that should stop the bot."""
    pass


def _get_logging_level(default: str = "DEBUG") -> int:
    lv = os.environ.get("LOG_LEVEL", default)

    try:
        lv = getattr(logging, lv)
    except AttributeError:
        warnings.warn(
            f"LOG_LEVEL has an invalid value of {lv}. Defaulting to {default}"
        )
        return getattr(logging, default)
    else:
        return lv


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON-structured logs."""

    STANDARD_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname', 'process',
        'processName', 'relativeCreated', 'thread', 'threadName', 'exc_info',
        'exc_text', 'stack_info', 'taskName'
    }

    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "file": record.pathname,
            "msg": record.getMessage(),
        }

        # Extract any extra fields as context
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self.STANDARD_ATTRS and not key.startswith('_')
        }
        if extra_fields:
            log_dict["context"] = extra_fields

        # Add exception info for errors
        if record.exc_info and record.levelno >= logging.ERROR:
            log_dict["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_dict, default=str, indent=2)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name, configured with JSON formatting."""
    logger = logging.getLogger(name)

    # Configure root logger only once
    # Use package name to ensure child loggers propagate correctly
    root = logging.getLogger("arxiv_sanity_bot")
    if not root.handlers:
        root.setLevel(_get_logging_level())
        root.propagate = False

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(JSONFormatter())
        root.addHandler(console)

        # File handler
        file_handler = logging.FileHandler("arxiv-sanity-bot.log")
        file_handler.setFormatter(JSONFormatter())
        root.addHandler(file_handler)

    return logger


# Legacy logger for backward compatibility during migration
logger = get_logger("arxiv_sanity_bot")
