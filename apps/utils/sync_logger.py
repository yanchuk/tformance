"""Structured logging for sync operations.

Provides JSON-formatted logging with automatic context injection for
team_id, repo_id, and task_id. Uses contextvars for thread-safe storage.

Usage:
    from apps.utils.sync_logger import get_sync_logger, sync_context, timed_operation

    logger = get_sync_logger(__name__)

    with sync_context(team_id="123", repo_id="456", task_id="celery-abc"):
        logger.info("Starting sync")

        with timed_operation(logger, "fetch_prs", pr_count=50):
            # ... do work
            pass  # Auto-logs duration_ms on exit
"""

import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

# Context variables for thread-safe storage
_team_id: ContextVar[str | None] = ContextVar("team_id", default=None)
_repo_id: ContextVar[str | None] = ContextVar("repo_id", default=None)
_task_id: ContextVar[str | None] = ContextVar("task_id", default=None)


class SyncContext:
    """Class providing access to sync context variables."""

    @classmethod
    def get_team_id(cls) -> str | None:
        """Get the current team_id from context."""
        return _team_id.get()

    @classmethod
    def get_repo_id(cls) -> str | None:
        """Get the current repo_id from context."""
        return _repo_id.get()

    @classmethod
    def get_task_id(cls) -> str | None:
        """Get the current task_id from context."""
        return _task_id.get()

    @classmethod
    def get_context_dict(cls) -> dict[str, str]:
        """Get all non-None context values as a dictionary.

        Returns:
            Dictionary with team_id, repo_id, and task_id keys (only if set)
        """
        context: dict[str, str] = {}
        if (team_id := cls.get_team_id()) is not None:
            context["team_id"] = team_id
        if (repo_id := cls.get_repo_id()) is not None:
            context["repo_id"] = repo_id
        if (task_id := cls.get_task_id()) is not None:
            context["task_id"] = task_id
        return context


@contextmanager
def sync_context(
    team_id: str | None = None,
    repo_id: str | None = None,
    task_id: str | None = None,
):
    """Context manager that sets team_id, repo_id, task_id in SyncContext.

    Nested contexts properly override values and restore them on exit.

    Args:
        team_id: Team identifier to set in context
        repo_id: Repository identifier to set in context
        task_id: Celery task identifier to set in context

    Usage:
        with sync_context(team_id="123", repo_id="456"):
            logger.info("This will include team_id and repo_id")
    """
    # Store old values for restoration
    old_team_id = _team_id.get()
    old_repo_id = _repo_id.get()
    old_task_id = _task_id.get()

    # Set new values (or keep old if not provided)
    team_token = _team_id.set(team_id if team_id is not None else old_team_id)
    repo_token = _repo_id.set(repo_id if repo_id is not None else old_repo_id)
    task_token = _task_id.set(task_id if task_id is not None else old_task_id)

    try:
        yield
    finally:
        # Restore old values
        _team_id.reset(team_token)
        _repo_id.reset(repo_token)
        _task_id.reset(task_token)


class SyncContextJsonFormatter(logging.Formatter):
    """JSON formatter that includes sync context in output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with context fields."""
        # Build base log entry
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from contextvars
        log_entry.update(SyncContext.get_context_dict())

        # Add extra fields from record (excluding standard attrs)
        standard_attrs = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "taskName",
            "message",
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_entry[key] = value

        return json.dumps(log_entry)


def _inject_context(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Inject sync context values into extra dict.

    Args:
        extra: Optional existing extra dict to extend

    Returns:
        New dict with context values merged in (does not mutate original)
    """
    result = dict(extra) if extra else {}
    result.update(SyncContext.get_context_dict())
    return result


class SyncLogger(logging.Logger):
    """Logger that auto-injects sync context into all log calls.

    Overrides standard log methods to automatically inject team_id, repo_id,
    and task_id from the current sync context into the extra dict.
    """

    def addHandler(self, hdlr: logging.Handler) -> None:
        """Override addHandler to set JSON formatter if none is set."""
        if hdlr.formatter is None:
            hdlr.setFormatter(SyncContextJsonFormatter())
        super().addHandler(hdlr)

    def debug(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Override debug to inject context."""
        kwargs["extra"] = _inject_context(kwargs.get("extra"))
        super().debug(msg, *args, **kwargs)

    def info(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Override info to inject context."""
        kwargs["extra"] = _inject_context(kwargs.get("extra"))
        super().info(msg, *args, **kwargs)

    def warning(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Override warning to inject context."""
        kwargs["extra"] = _inject_context(kwargs.get("extra"))
        super().warning(msg, *args, **kwargs)

    def error(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Override error to inject context."""
        kwargs["extra"] = _inject_context(kwargs.get("extra"))
        super().error(msg, *args, **kwargs)

    def critical(self, msg: object, *args: object, **kwargs: Any) -> None:
        """Override critical to inject context."""
        kwargs["extra"] = _inject_context(kwargs.get("extra"))
        super().critical(msg, *args, **kwargs)


# Registry to track configured loggers
_configured_loggers: set[str] = set()


def get_sync_logger(name: str) -> logging.Logger:
    """Get a logger that includes sync context in JSON output.

    Args:
        name: Logger name (typically __name__)

    Returns:
        A logging.Logger instance configured for sync logging
    """
    # Set the logger class before getting the logger
    old_class = logging.getLoggerClass()
    logging.setLoggerClass(SyncLogger)

    logger = logging.getLogger(name)

    # Restore the old class
    logging.setLoggerClass(old_class)

    # Configure formatter only once per logger name
    if name not in _configured_loggers:
        # Only add our formatter if no handlers exist
        # This allows the logger to work with existing handlers too
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(SyncContextJsonFormatter())
            logger.addHandler(handler)
        _configured_loggers.add(name)

    return logger


@contextmanager
def timed_operation(logger: logging.Logger, operation: str, **extra_fields: Any):
    """Context manager that logs duration_ms when block exits.

    Args:
        logger: Logger to use for output
        operation: Name of the operation being timed
        **extra_fields: Additional fields to include in log output

    Yields:
        None - control returns to the caller's block

    Usage:
        with timed_operation(logger, "fetch_prs", repo_count=5):
            # ... do work
            pass  # Auto-logs duration_ms on exit
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_extra: dict[str, Any] = {
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            **extra_fields,
            **SyncContext.get_context_dict(),
        }

        logger.info(f"{operation} completed", extra=log_extra)
