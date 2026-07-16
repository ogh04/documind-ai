import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        event = getattr(record, "event", None)
        if event is not None:
            log_payload["event"] = event

        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            log_payload.update(extra_fields)

        if record.exc_info:
            log_payload["error_type"] = record.exc_info[0].__name__
            log_payload["error_message"] = str(record.exc_info[1])
            log_payload["traceback"] = traceback.format_exception(
                *record.exc_info
            )

        return json.dumps(
            log_payload,
            ensure_ascii=False,
            default=str,
        )


def setup_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(JsonFormatter())

    root_logger.addHandler(stream_handler)

    # Keep our application logs visible.
    logging.getLogger("app").setLevel(logging.INFO)

    # Reduce noisy server / third-party logs.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)

    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers.base.model").setLevel(logging.WARNING)

    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(
    logger: logging.Logger,
    event: str,
    message: str,
    level: int = logging.INFO,
    **fields: Any,
) -> None:
    logger.log(
        level,
        message,
        extra={
            "event": event,
            "extra_fields": fields,
        },
    )