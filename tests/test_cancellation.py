"""User Story 2 (owner cancels) and User Story 3 (customer self-cancels).

Both must immediately free the slot (FR-005, FR-011), and neither should
ever double-cancel or crash on a stale/unknown token or id.
"""

import re

from tests.conftest import TEST_PASSCODE, a_future_slot


def _book(client, slot=None):
    slot = slot or a_future_slot()
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")
    resp = client.post(
        "/book",
        data={"slot_start": slot_str, "customer_name": "Alan Turing", "customer_phone": "555-0142"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    cancel_token = resp.headers["location"].removeprefix("/confirmation/")
    return slot_str, cancel_token


def test_owner_can_cancel_booking(client):
    slot_str, _cancel_token = _book(client)

    client.post("/owner", data={"passcode": TEST_PASSCODE})
    bookings_page = client.get("/owner/bookings")
    match = re.search(r'/owner/bookings/(\d+)/cancel', bookings_page.text)
    assert match, "expected a cancel action for the booking"
    booking_id = match.group(1)

    cancel_resp = client.post(f"/owner/bookings/{booking_id}/cancel", follow_redirects=False)
    assert cancel_resp.status_code == 303

    # The slot must be bookable again immediately.
    home = client.get("/")
    assert slot_str in home.text

    bookings_page_after = client.get("/owner/bookings")
    assert "No upcoming bookings" in bookings_page_after.text


def test_customer_can_cancel_via_link(client):
    slot_str, cancel_token = _book(client)

    prompt = client.get(f"/cancel/{cancel_token}")
    assert prompt.status_code == 200
    assert "Yes, cancel my booking" in prompt.text

    submit = client.post(f"/cancel/{cancel_token}")
    assert submit.status_code == 200
    assert "Booking cancelled" in submit.text

    home = client.get("/")
    assert slot_str in home.text


def test_reusing_cancel_link_is_safe(client):
    _slot_str, cancel_token = _book(client)

    first = client.post(f"/cancel/{cancel_token}")
    assert "Booking cancelled" in first.text

    second = client.post(f"/cancel/{cancel_token}")
    assert second.status_code == 200
    assert "no longer valid" in second.text.lower()

    unknown = client.post("/cancel/this-token-was-never-issued")
    assert unknown.status_code == 200
    assert "no longer valid" in unknown.text.lower()
