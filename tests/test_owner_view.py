"""User Story 2: the owner views upcoming bookings behind a shared passcode."""

from tests.conftest import TEST_PASSCODE, a_future_slot


def _make_booking(client, slot=None):
    slot = slot or a_future_slot()
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")
    resp = client.post(
        "/book",
        data={"slot_start": slot_str, "customer_name": "Grace Hopper", "customer_phone": "555-0199"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    return slot_str


def test_owner_bookings_requires_session(client):
    resp = client.get("/owner/bookings", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/owner"


def test_passcode_gate(client):
    _make_booking(client)

    # Wrong passcode: refused, and no booking data anywhere in the response.
    wrong = client.post("/owner", data={"passcode": "definitely-wrong"})
    assert wrong.status_code == 401
    assert "Grace Hopper" not in wrong.text

    # Correct passcode: granted, and the booking appears.
    right = client.post("/owner", data={"passcode": TEST_PASSCODE}, follow_redirects=False)
    assert right.status_code == 303
    assert right.headers["location"] == "/owner/bookings"

    bookings_page = client.get("/owner/bookings")
    assert bookings_page.status_code == 200
    assert "Grace Hopper" in bookings_page.text
