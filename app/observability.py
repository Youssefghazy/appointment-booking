"""Optional Langfuse tracing for the app's key business events.

This app has no LLM calls, so there's nothing for Langfuse's usual
prompt/completion tracking to do here -- but Langfuse also works as a
plain tracing backend. `record_event()` below opens one short span per
meaningful business event (a booking attempt and its outcome, a
cancellation, an owner login) so you get a searchable timeline on
langfuse.com, without sending any customer name/email off this server:
callers here are only ever passed small, non-personal fields (a slot
time, a booking id, a success/fail reason).

Fully optional and fails safe:
- If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY aren't set, or the
  `langfuse` package isn't installed, `ENABLED` is False and
  `record_event()` / `flush()` do nothing.
- If Langfuse *is* configured but a call to it fails for any reason
  (network hiccup, bad keys, ...), that failure is logged and swallowed
  here -- it must never break an actual booking request.
"""

import logging
import os

logger = logging.getLogger("observability")

_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")

_client = None
ENABLED = False

if _PUBLIC_KEY and _SECRET_KEY:
    try:
        from langfuse import get_client

        _client = get_client()
        ENABLED = True
        logger.info(
            "langfuse_enabled",
            extra={"host": os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")},
        )
    except Exception:  # pragma: no cover - optional dependency, must not crash startup
        logger.warning("langfuse_init_failed", exc_info=True)
        _client = None
        ENABLED = False
else:
    logger.info("langfuse_disabled", extra={"reason": "no_keys_configured"})


def record_event(name: str, **fields) -> None:
    """Records one already-finished business event as a Langfuse span.

    No-op if Langfuse isn't configured. `fields` should be small and
    JSON-safe (strings, numbers, booleans) and must never contain a
    customer's name or email.
    """
    if not ENABLED:
        return
    try:
        with _client.start_as_current_observation(as_type="span", name=name, input=fields):
            pass
    except Exception:  # pragma: no cover - tracing must never break a request
        logger.warning("langfuse_record_failed", exc_info=True)


def flush() -> None:
    """Sends any buffered events immediately. Call this on shutdown --
    Langfuse normally batches and sends in the background, so without a
    final flush the last few events from a short-lived process could be
    lost.
    """
    if ENABLED and _client is not None:
        try:
            _client.flush()
        except Exception:  # pragma: no cover
            logger.warning("langfuse_flush_failed", exc_info=True)
