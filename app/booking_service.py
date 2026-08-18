"""All the business logic for the booking system lives here.

`app/main.py` (the web layer) never talks to SQLite directly -- it only
calls functions in this module. That keeps the "what are the rules" logic
separate from "how do we render a page", which makes both halves easier to
read and test on their own.
"""

import secrets
import sqlite3
from datetime import date, datetime, timedelta

from app import config

SLOT_FORMAT = "%Y-%m-%dT%H:%M:%S"


class InvalidBookingError(Exception):
    """Raised when the customer's submitted details fail validation.

    `field` identifies which form field was the problem, so the web layer
    can show the error next to the right input.
    """

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


class SlotAlreadyBookedError(Exception):
    """Raised when a booking attempt loses the race for a slot.

    This is the exception that proves Constitution Principle II: it can
    only be raised because the database's unique index rejected the
    write, not because of an application-level "check first" that could
    itself race.
    """


# ---------------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------------


def _generate_valid_slots(now: datetime) -> list[datetime]:
    """Every bookable slot start time from `now` through the booking window.

    A slot is valid if: its day is a business day, it starts at or after
    business opening and finishes at or before closing, it's still in the
    future relative to `now`, and it falls within BOOKING_WINDOW_DAYS.
    """
    slots: list[datetime] = []
    slot_length = timedelta(minutes=config.SLOT_MINUTES)
    window_end = now + timedelta(days=config.BOOKING_WINDOW_DAYS)

    day = now.date()
    end_date = window_end.date()
    while day <= end_date:
        if day.weekday() in config.BUSINESS_DAYS:
            slot_start = datetime(day.year, day.month, day.day, config.BUSINESS_START_HOUR, 0)
            day_close = datetime(day.year, day.month, day.day, config.BUSINESS_END_HOUR, 0)
            while slot_start + slot_length <= day_close:
                if slot_start > now and slot_start <= window_end:
                    slots.append(slot_start)
                slot_start += slot_length
        day += timedelta(days=1)

    return slots


def is_valid_slot(slot_start: datetime, now: datetime | None = None) -> bool:
    """True if `slot_start` is a real, currently-bookable slot (FR-007)."""
    now = now or datetime.now()
    return slot_start in _generate_valid_slots(now)


def list_available_slots(conn: sqlite3.Connection, now: datetime | None = None) -> list[datetime]:
    """All valid slots that don't already have an active booking (FR-001)."""
    now = now or datetime.now()
    all_slots = _generate_valid_slots(now)

    rows = conn.execute("SELECT slot_start FROM bookings WHERE status = 'active'").fetchall()
    booked = {datetime.strptime(row["slot_start"], SLOT_FORMAT) for row in rows}

    return [slot for slot in all_slots if slot not in booked]


def slots_by_date(conn: sqlite3.Connection, now: datetime | None = None) -> dict[date, list[datetime]]:
    """Available slots grouped by calendar day -- the shape the day-picker
    calendar and the "times for this day" list both need.
    """
    grouped: dict[date, list[datetime]] = {}
    for slot in list_available_slots(conn, now):
        grouped.setdefault(slot.date(), []).append(slot)
    return grouped


def is_business_day(day: date) -> bool:
    """True if `day`'s weekday is one of the configured business days."""
    return day.weekday() in config.BUSINESS_DAYS


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise InvalidBookingError("customer_name", "Please enter your name.")
    return cleaned


def _validate_email(email: str | None) -> str | None:
    if not email:
        return None
    cleaned = email.strip()
    if not cleaned:
        return None
    if cleaned.count("@") != 1:
        raise InvalidBookingError("customer_email", "Please enter a valid email address.")
    local_part, _, domain_part = cleaned.partition("@")
    if not local_part or not domain_part or "." not in domain_part:
        raise InvalidBookingError("customer_email", "Please enter a valid email address.")
    return cleaned


def _parse_slot(slot_start_raw: str) -> datetime:
    try:
        return datetime.strptime(slot_start_raw, SLOT_FORMAT)
    except (TypeError, ValueError):
        raise InvalidBookingError("slot_start", "Please choose a valid time slot.")


# ---------------------------------------------------------------------------
# Booking / cancellation
# ---------------------------------------------------------------------------


def create_booking(
    conn: sqlite3.Connection,
    slot_start_raw: str,
    customer_name: str,
    customer_email: str | None = None,
    now: datetime | None = None,
) -> sqlite3.Row:
    """Validates input, then atomically books the slot (FR-002, FR-003, FR-008).

    Raises InvalidBookingError for bad input, or SlotAlreadyBookedError if
    the slot was taken by someone else (including a genuine race -- this
    is where Constitution Principle II is enforced).
    """
    now = now or datetime.now()

    slot_start = _parse_slot(slot_start_raw)
    name = _validate_name(customer_name)
    email = _validate_email(customer_email)

    if not is_valid_slot(slot_start, now):
        raise InvalidBookingError(
            "slot_start",
            "That slot is outside business hours, in the past, or too far ahead.",
        )

    cancel_token = secrets.token_urlsafe(24)
    created_at = now.strftime(SLOT_FORMAT)
    slot_start_str = slot_start.strftime(SLOT_FORMAT)

    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """
            INSERT INTO bookings
                (slot_start, customer_name, customer_email,
                 status, cancel_token, created_at)
            VALUES (?, ?, ?, 'active', ?, ?)
            """,
            (slot_start_str, name, email, cancel_token, created_at),
        )
    except sqlite3.IntegrityError as exc:
        conn.execute("ROLLBACK")
        if "slot_start" in str(exc):
            # The unique index did its job: someone else booked this exact
            # slot in the moment between us reading the slot list and
            # writing this insert.
            raise SlotAlreadyBookedError(
                "Sorry, that slot was just taken. Please pick another."
            ) from exc
        # Astronomically unlikely (a cancel_token collision), but don't
        # mislabel it as a booking conflict if it somehow happens.
        raise
    else:
        conn.execute("COMMIT")

    return conn.execute(
        "SELECT * FROM bookings WHERE cancel_token = ?", (cancel_token,)
    ).fetchone()


def get_booking_by_token(conn: sqlite3.Connection, cancel_token: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM bookings WHERE cancel_token = ?", (cancel_token,)
    ).fetchone()


def list_active_bookings(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """All upcoming active bookings, for the owner's view (FR-006)."""
    return conn.execute(
        "SELECT * FROM bookings WHERE status = 'active' ORDER BY slot_start ASC"
    ).fetchall()


def cancel_booking(
    conn: sqlite3.Connection,
    *,
    booking_id: int | None = None,
    cancel_token: str | None = None,
    by: str,
    now: datetime | None = None,
) -> dict:
    """Cancels a booking by id (owner) or token (customer) (FR-005, FR-011).

    Safe to call on an already-cancelled or unknown booking: it never
    raises for that case, it just reports why nothing happened, so a
    reused/stale cancellation link can never crash the app or cancel
    someone else's booking.
    """
    if by not in ("owner", "customer"):
        raise ValueError("by must be 'owner' or 'customer'")
    if (booking_id is None) == (cancel_token is None):
        raise ValueError("pass exactly one of booking_id or cancel_token")

    now = now or datetime.now()

    conn.execute("BEGIN IMMEDIATE")
    if booking_id is not None:
        row = conn.execute("SELECT id, status FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    else:
        row = conn.execute(
            "SELECT id, status FROM bookings WHERE cancel_token = ?", (cancel_token,)
        ).fetchone()

    if row is None:
        conn.execute("ROLLBACK")
        return {"ok": False, "reason": "not_found"}

    if row["status"] == "cancelled":
        conn.execute("ROLLBACK")
        return {"ok": False, "reason": "already_cancelled"}

    conn.execute(
        "UPDATE bookings SET status = 'cancelled', cancelled_at = ?, cancelled_by = ? WHERE id = ?",
        (now.strftime(SLOT_FORMAT), by, row["id"]),
    )
    conn.execute("COMMIT")
    return {"ok": True, "booking_id": row["id"]}
