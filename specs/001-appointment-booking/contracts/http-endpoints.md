# Phase 1 Contracts: HTTP Endpoints

This app is server-rendered (Jinja2 HTML), so the "contract" is the set of
routes, their inputs, and their outcomes — not a JSON API schema. Form
posts redirect (303) to a result page on success, following standard
POST-redirect-GET practice so refreshing the result page never re-submits
a booking.

## `GET /`

Customer booking page. Three stages, all driven by query params and shown
one at a time (business hours minus active bookings, next 30 days, past
slots excluded):

- No params: a compact list of days that currently have open slots.
- `?day=YYYY-MM-DD`: that day's open times, if the day still resolves to
  something bookable (otherwise falls back to the day list with a
  message).
- `?day=YYYY-MM-DD&slot=...`: the name/email form for that slot, if it
  still resolves to something bookable (otherwise falls back to the time
  list with a message).

- **Response**: 200, HTML.

## `POST /book`

Create a booking.

- **Body (form-encoded)**: `slot_start` (required), `customer_name`
  (required), `customer_email` (optional).
- **Success**: 303 redirect to `GET /confirmation/{cancel_token}`.
- **Validation failure** (FR-008): 422, re-renders the booking page with a
  specific error message and the customer's other input preserved.
- **Slot no longer available** (FR-003, FR-007): 409, re-renders the
  booking page with a "this slot was just taken, please pick another"
  message and a refreshed slot list.

## `GET /confirmation/{cancel_token}`

Booking confirmation page. Shows the booked slot's time and a cancellation
link built from `cancel_token`.

- **Success**: 200, HTML.
- **Unknown/invalid token**: 404, generic "booking not found" page.

## `GET /cancel/{cancel_token}`

Shows a "are you sure you want to cancel this booking?" confirmation page
for the customer (does not cancel yet — this is a GET, so it must be
side-effect free).

- **Success**: 200, HTML, with a form that POSTs to the same path.
- **Already cancelled / unknown token**: 200, HTML explaining the link is
  no longer valid (spec Edge Cases / User Story 3 Acceptance Scenario 2).

## `POST /cancel/{cancel_token}`

Actually cancels the booking (FR-005).

- **Success**: sets `status='cancelled'`, `cancelled_by='customer'`; 303
  redirect to a "booking cancelled" result page. The freed slot is
  immediately excluded from `active` bookings, so it reappears on `GET /`.
- **Already cancelled / unknown token**: no state change; re-renders the
  "link no longer valid" message.

## `GET /owner`

Owner passcode form (if not already authenticated via session cookie) or,
if authenticated, redirects to `GET /owner/bookings`.

- **Response**: 200, HTML.

## `POST /owner`

Submit the owner passcode.

- **Body (form-encoded)**: `passcode`.
- **Correct passcode**: sets a signed session cookie; 303 redirect to
  `GET /owner/bookings` (FR-006).
- **Incorrect passcode**: 401, re-renders the passcode form with a generic
  "incorrect passcode" message — no distinction from "no bookings exist"
  (spec Edge Cases, FR-010).

## `GET /owner/bookings`

Owner's view of all upcoming active bookings, each with a "cancel" action.
Requires a valid owner session cookie; otherwise redirects to `GET /owner`.

- **Response**: 200, HTML.

## `POST /owner/bookings/{booking_id}/cancel`

Owner cancels a specific booking (FR-011). Requires a valid owner session
cookie.

- **Success**: sets `status='cancelled'`, `cancelled_by='owner'`; 303
  redirect back to `GET /owner/bookings`. The slot is immediately available
  again on `GET /`.
- **Unknown booking / already cancelled**: no state change; still a 303
  redirect back to `GET /owner/bookings` (the cancel is a safe no-op — see
  `booking_service.cancel_booking`), not a 404. No crash either way.
- **No valid session**: 303 redirect to `GET /owner`.

## `POST /owner/logout`

Clears the owner session cookie; 303 redirect to `GET /owner`.
