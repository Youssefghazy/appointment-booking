# Quickstart: Validate the Appointment Booking App End-to-End

## Prerequisites

- Python 3.11+
- A terminal in the repository root

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # then edit .env to set OWNER_PASSCODE
```

## Run

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/` in a browser.

## Manual validation scenarios

1. **Book a slot (User Story 1)**: On `/`, pick any listed open slot, enter
   a name and phone number, submit. Expect a confirmation page with a
   cancellation link, and the slot no longer listed as available on a page
   refresh.
2. **Reject invalid input (FR-008)**: Try submitting the booking form with
   an empty name. Expect a clear validation error and no new booking.
3. **Owner view (User Story 2)**: Visit `/owner`, enter the passcode from
   `.env`, and confirm the booking from step 1 appears with its details.
   Try an incorrect passcode first and confirm access is refused.
4. **Owner cancels (FR-011)**: From the owner bookings list, cancel the
   booking. Confirm it's gone from the owner list and the slot is
   available again on `/`.
5. **Customer self-cancel (User Story 3)**: Make a new booking, follow its
   confirmation page's cancellation link, confirm the cancellation. Confirm
   the slot is available again on `/`, and that reopening the same link
   afterward shows "no longer valid" rather than cancelling twice.

## Automated validation

```bash
pytest
```

Expected: all tests pass, including `tests/test_double_booking.py`, which
fires concurrent booking attempts at the same slot from multiple threads
and asserts exactly one succeeds — the automated proof of Constitution
Principle II / spec SC-002.
