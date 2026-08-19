"""Structured (JSON) logging setup.

Why JSON: on a host like Render, everything the app prints to stdout gets
collected as raw text log lines. Plain sentences are fine for a human
tailing logs locally, but they're hard to search or filter -- e.g.
"show me every request with status_code >= 500". One JSON object per
line is still readable, but a log viewer (or a quick `jq` pipe) can also
filter it by field.

Deliberately dependency-free: a small `logging.Formatter` subclass is
enough, no extra package needed for this part.
"""

import json
import logging
import sys
from datetime import datetime, timezone

# Fields every standard LogRecord already carries that we don't want to
# duplicate in the JSON body (internal/noisy attributes).
_RESERVED = set(
    logging.LogRecord(
        name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
    ).__dict__.keys()
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single-line JSON object.

    Anything passed via `logger.info("event_name", extra={...})` is
    merged in as its own top-level key, so `extra={"booking_id": 5}`
    shows up as `"booking_id": 5` in the JSON line.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value

        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """Configures the root logger to emit one JSON object per line to
    stdout. Safe to call more than once (e.g. under `--reload`) -- it
    clears existing handlers first so log lines never get duplicated.
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
