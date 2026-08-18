"""Reads configuration from environment variables.

Everything the app needs to know that could change between environments
(the owner's passcode, business hours, ...) lives here, in one place. See
.env.example for what each setting means.
"""

import os
import secrets

from dotenv import load_dotenv

# Loads variables from a .env file in the project root, if present.
# (In production/deployment you'd usually set real environment variables
# instead, and .env just wouldn't exist -- load_dotenv() is a no-op then.)
load_dotenv()


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _get_int_list(name: str, default: list[int]) -> list[int]:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return [int(part) for part in raw.split(",")]


# The shared passcode the owner enters to see the bookings list.
# Deliberately has NO default -- the app should fail loudly at startup
# rather than silently run with a guessable default passcode.
OWNER_PASSCODE = os.environ.get("OWNER_PASSCODE")

# Business hours: the service is bookable from BUSINESS_START_HOUR up to
# (but not including) BUSINESS_END_HOUR, on the given days of the week.
# Days follow Python's Monday=0 ... Sunday=6 convention.
BUSINESS_START_HOUR = _get_int("BUSINESS_START_HOUR", 9)
BUSINESS_END_HOUR = _get_int("BUSINESS_END_HOUR", 17)
BUSINESS_DAYS = _get_int_list("BUSINESS_DAYS", [0, 1, 2, 3, 4])  # Mon-Fri

# Every appointment is this many minutes long.
SLOT_MINUTES = _get_int("SLOT_MINUTES", 30)

# Customers can only book within this many days from now.
BOOKING_WINDOW_DAYS = _get_int("BOOKING_WINDOW_DAYS", 30)

# Secret key used to sign the owner's session cookie. If one isn't set,
# generate a random one at startup -- fine for local/demo use; it just
# means the owner's session doesn't survive a server restart.
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32)

# Where the SQLite database file lives.
DB_PATH = os.environ.get("DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "booking.db"
))


def require_owner_passcode() -> str:
    """Returns the configured owner passcode, or raises a clear error.

    Called at startup so a missing passcode fails immediately and
    obviously, instead of the owner view silently accepting anything.
    """
    if not OWNER_PASSCODE:
        raise RuntimeError(
            "OWNER_PASSCODE is not set. Copy .env.example to .env and set "
            "OWNER_PASSCODE before starting the app."
        )
    return OWNER_PASSCODE
