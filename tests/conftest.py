"""Shared pytest fixtures.

Every test gets its own throwaway SQLite file (via pytest's `tmp_path`),
so tests never interfere with each other or with a real `data/booking.db`.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make sure `app` is importable when pytest is run from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("OWNER_PASSCODE", "test-passcode")

from app import booking_service, config, db, main  # noqa: E402

TEST_PASSCODE = "test-passcode"


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Points the app at a fresh, empty SQLite file for this test only."""
    db_path = tmp_path / "test_booking.db"
    monkeypatch.setattr(config, "DB_PATH", str(db_path))
    monkeypatch.setattr(config, "OWNER_PASSCODE", TEST_PASSCODE)
    db.init_db()
    return str(db_path)


@pytest.fixture
def conn(temp_db):
    """A direct database connection, for tests that call booking_service functions directly."""
    connection = db.get_connection()
    yield connection
    connection.close()


@pytest.fixture
def client(temp_db):
    """An HTTP test client wired up to the same temp database."""
    with TestClient(main.app) as test_client:
        yield test_client


def a_future_slot(now: datetime | None = None) -> datetime:
    """Returns the first currently-valid, currently-open slot start time.

    Uses the app's own slot-generation logic (business hours, booking
    window, "not in the past") so tests never hardcode a date that could
    become stale or fall on a non-business day.
    """
    now = now or datetime.now()
    slots = booking_service._generate_valid_slots(now)
    assert slots, "no valid slots generated -- check business-hours config"
    return slots[0]


def a_slot_outside_business_hours(now: datetime | None = None) -> datetime:
    """A time on a valid business day, but before opening -- always invalid."""
    now = now or datetime.now()
    valid = a_future_slot(now)
    # One hour before business opens on the same day as a valid slot.
    return datetime(valid.year, valid.month, valid.day, 0, 0) + timedelta(
        hours=max(config.BUSINESS_START_HOUR - 1, 0)
    )


def a_slot_in_the_past(now: datetime | None = None) -> datetime:
    """A business-hours time slot that has already happened."""
    now = now or datetime.now()
    return datetime(now.year, now.month, now.day, config.BUSINESS_START_HOUR, 0) - timedelta(days=365)
