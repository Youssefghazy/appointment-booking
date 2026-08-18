"""User Story 1: a customer views open slots and books one."""

from datetime import timedelta

from tests.conftest import a_future_slot, a_slot_in_the_past, a_slot_outside_business_hours


def test_home_page_lists_available_slots(client):
    slot = a_future_slot()
    day_str = slot.strftime("%Y-%m-%d")

    # The calendar itself (no day picked yet) links to the day.
    response = client.get("/")
    assert response.status_code == 200
    assert f"/?day={day_str}" in response.text

    # Picking that day shows its open times.
    day_response = client.get(f"/?day={day_str}")
    assert slot.strftime("%Y-%m-%dT%H:%M:%S") in day_response.text


def test_successful_booking_returns_confirmation(client):
    slot = a_future_slot()
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")
    day_str = slot.strftime("%Y-%m-%d")

    response = client.post(
        "/book",
        data={
            "slot_start": slot_str,
            "customer_name": "Ada Lovelace",
            "customer_email": "ada@example.com",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/confirmation/")

    confirmation = client.get(location)
    assert confirmation.status_code == 200
    assert "You&#39;re booked" in confirmation.text or "You're booked" in confirmation.text
    assert "Cancel this booking" in confirmation.text

    # The booked slot must no longer be offered to other customers.
    day_page = client.get(f"/?day={day_str}")
    assert slot_str not in day_page.text


def test_invalid_input_rejected(client):
    slot = a_future_slot()
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")
    day_str = slot.strftime("%Y-%m-%d")

    # Empty name
    resp = client.post(
        "/book",
        data={"slot_start": slot_str, "customer_name": ""},
    )
    assert resp.status_code == 422
    assert "name" in resp.text.lower()

    # Malformed email
    resp = client.post(
        "/book",
        data={
            "slot_start": slot_str,
            "customer_name": "Ada",
            "customer_email": "not-an-email",
        },
    )
    assert resp.status_code == 422

    # None of the above should have created a booking -- the slot is still offered.
    day_page = client.get(f"/?day={day_str}")
    assert slot_str in day_page.text


def test_booking_rejected_outside_business_hours_or_past(client):
    outside_hours = a_slot_outside_business_hours()
    resp = client.post(
        "/book",
        data={
            "slot_start": outside_hours.strftime("%Y-%m-%dT%H:%M:%S"),
            "customer_name": "Ada",
        },
    )
    assert resp.status_code == 422

    past_slot = a_slot_in_the_past()
    resp = client.post(
        "/book",
        data={
            "slot_start": past_slot.strftime("%Y-%m-%dT%H:%M:%S"),
            "customer_name": "Ada",
        },
    )
    assert resp.status_code == 422
