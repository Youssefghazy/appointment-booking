"""Constitution Principle II / spec FR-003 / SC-002: no double-booking,
even when booking attempts race each other.

Both tests fire multiple concurrent attempts at the exact same slot and
assert that exactly one succeeds -- the core guarantee this whole project
exists to prove.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from app import booking_service, db
from tests.conftest import a_future_slot

THREAD_COUNT = 12


def test_concurrent_service_calls_only_one_succeeds(temp_db):
    """Hits booking_service.create_booking() directly from real OS threads,
    each with its own SQLite connection to the same on-disk file -- this
    exercises the actual database locking + unique-index behavior, not
    just application code."""
    slot = a_future_slot()
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")

    barrier = threading.Barrier(THREAD_COUNT)
    successes = []
    conflicts = []
    errors = []

    def attempt(i: int):
        conn = db.get_connection()
        try:
            barrier.wait()  # line everyone up to maximize the actual race
            booking_service.create_booking(
                conn, slot_str, f"Customer {i}", "555-0100"
            )
            successes.append(i)
        except booking_service.SlotAlreadyBookedError:
            conflicts.append(i)
        except Exception as exc:  # pragma: no cover - would indicate a real bug
            errors.append((i, exc))
        finally:
            conn.close()

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(THREAD_COUNT)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"unexpected errors during concurrent booking: {errors}"
    assert len(successes) == 1, f"expected exactly 1 success, got {len(successes)}: {successes}"
    assert len(conflicts) == THREAD_COUNT - 1

    # Confirm the database agrees: exactly one active booking for this slot.
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT COUNT(*) AS n FROM bookings WHERE slot_start = ? AND status = 'active'",
            (slot_str,),
        ).fetchone()
    finally:
        conn.close()
    assert rows["n"] == 1


def test_concurrent_http_requests_only_one_succeeds(client):
    """Same race, exercised through the actual HTTP layer with TestClient."""
    slot = a_future_slot()
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")

    def attempt(i: int):
        return client.post(
            "/book",
            data={
                "slot_start": slot_str,
                "customer_name": f"HTTP Customer {i}",
                "customer_phone": "555-0100",
            },
            follow_redirects=False,
        )

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as pool:
        futures = [pool.submit(attempt, i) for i in range(THREAD_COUNT)]
        responses = [f.result() for f in as_completed(futures)]

    successes = [r for r in responses if r.status_code == 303]
    conflicts = [r for r in responses if r.status_code == 409]

    assert len(successes) == 1, f"expected exactly 1 successful booking, got {len(successes)}"
    assert len(conflicts) == THREAD_COUNT - 1
