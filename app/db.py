"""SQLite connection handling and schema setup.

This is the ONLY module that talks to the database file directly. Keeping
all the SQL in one small module (plus booking_service.py, which uses it)
makes the whole data layer easy to read in one sitting -- there's no ORM
translating things behind the scenes.
"""

import os
import sqlite3

from app import config

# The single table this whole app needs. See specs/001-appointment-booking/
# data-model.md for the full field-by-field explanation and the reasoning
# behind the partial unique index below.
SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_start     TEXT NOT NULL,
    customer_name  TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_email TEXT,
    status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    cancel_token   TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    cancelled_at   TEXT,
    cancelled_by   TEXT
);

-- THE core guarantee: at most one ACTIVE booking can ever exist for a
-- given slot_start. Two inserts racing for the same slot_start can never
-- both succeed -- the database itself rejects the second one. Cancelled
-- bookings don't count, so a freed slot is immediately bookable again.
CREATE UNIQUE INDEX IF NOT EXISTS idx_one_active_booking_per_slot
ON bookings (slot_start)
WHERE status = 'active';

-- Cancellation links must uniquely identify one booking.
CREATE UNIQUE INDEX IF NOT EXISTS idx_cancel_token
ON bookings (cancel_token);
"""


def get_connection() -> sqlite3.Connection:
    """Opens a fresh connection to the SQLite database file.

    A new connection per request/thread is the simplest safe pattern for
    sqlite3 in a multi-threaded server -- connections aren't shared, so
    there's no need to reason about thread-safety of a single connection
    object. `isolation_level=None` puts the connection in autocommit mode,
    so *we* control exactly when a transaction begins (see
    booking_service.create_booking), instead of relying on sqlite3's
    implicit transaction handling.
    """
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    # WAL mode lets reads (e.g. listing slots) proceed without blocking on
    # a concurrent write, and vice versa -- good for a small local app.
    conn.execute("PRAGMA journal_mode=WAL")
    # If a writer can't get the lock immediately (another booking write is
    # in progress), wait up to 5s instead of failing right away. This is
    # what makes concurrent booking attempts queue up safely rather than
    # erroring out with "database is locked".
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Creates the bookings table and indexes if they don't already exist.

    Safe to call every time the app starts -- CREATE ... IF NOT EXISTS is
    a no-op once the schema is already there.
    """
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
    finally:
        conn.close()
