"""The booking page has exactly three stages -- day, time, details -- and
at any moment only one of them should be visible. These tests pin down
that progressive-disclosure behavior directly, since it's easy for a
future change to accidentally show two stages at once (or none).
"""

from tests.conftest import a_future_slot


def test_stage_one_shows_only_the_day_picker(client):
    """No `day` query param -> day cards only, no times, no details form."""
    slot = a_future_slot()
    day_str = slot.strftime("%Y-%m-%d")

    response = client.get("/")
    assert response.status_code == 200
    assert f"/?day={day_str}" in response.text  # a day card links to it
    assert 'name="slot"' not in response.text  # no time radios yet
    assert 'name="customer_name"' not in response.text  # no details form yet


def test_stage_two_shows_only_that_days_times(client):
    """A valid `day` -> that day's times only, no details form yet."""
    slot = a_future_slot()
    day_str = slot.strftime("%Y-%m-%d")
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")

    response = client.get(f"/?day={day_str}")
    assert response.status_code == 200
    assert f'value="{slot_str}"' in response.text
    assert 'name="customer_name"' not in response.text  # details form not shown yet
    assert "Change day" in response.text  # a way back to stage one


def test_stage_three_shows_summary_and_details_form(client):
    """A valid `day` + `slot` -> booking summary and the details form."""
    slot = a_future_slot()
    day_str = slot.strftime("%Y-%m-%d")
    slot_str = slot.strftime("%Y-%m-%dT%H:%M:%S")

    response = client.get(f"/?day={day_str}&slot={slot_str}")
    assert response.status_code == 200
    assert 'name="customer_name"' in response.text
    assert f'value="{slot_str}"' in response.text  # carried as a hidden field
    assert "Change time" in response.text
    assert "Change day" in response.text


def test_unavailable_day_falls_back_to_day_stage_with_a_message(client):
    """A `day` that doesn't resolve to anything bookable (bad bookmark,
    stale link, or just a typo) shouldn't silently ignore the param --
    it should say so and land back on the day picker."""
    response = client.get("/?day=2099-01-01")
    assert response.status_code == 200
    assert "no longer available" in response.text.lower()
    assert 'name="slot"' not in response.text
    assert 'name="customer_name"' not in response.text


def test_stale_slot_falls_back_to_time_stage_with_a_message(client):
    """A valid day but a `slot` that isn't actually one of its open
    times (e.g. someone else just booked it) should bounce back to the
    time-picking stage, not silently drop to the day picker or crash."""
    slot = a_future_slot()
    day_str = slot.strftime("%Y-%m-%d")

    response = client.get(f"/?day={day_str}&slot=2099-01-01T09:00:00")
    assert response.status_code == 200
    assert "just taken" in response.text.lower()
    assert 'name="slot"' in response.text  # back on the time-picking stage
    assert 'name="customer_name"' not in response.text
