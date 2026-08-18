# Feature Specification: Single-Service Appointment Booking

**Feature Branch**: `001-appointment-booking`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "A small appointment booking system for one fixed
service and one calendar, with no customer accounts. Customers view open
slots and book one by giving their name and contact info; a slot can never
be double-booked, even under concurrent booking attempts. Business hours are
Mon-Fri 9AM-5PM with 30-minute slots. Customers can cancel their own booking
via a private link, which immediately frees the slot. The owner views all
upcoming bookings after entering a shared passcode (no owner account
system)." Derived from the student's handwritten `spec.md` and the answered
clarification questions in `CLARIFICATIONS.md`.

## Clarifications

### Session 2026-08-18

- Q: Your handwritten spec.md said the owner can "cancel a booking." Should the owner also be able to cancel a booking from their own view, not just view it? → A: Yes — the owner's view includes a cancel action per booking, and owner-initiated cancellation frees the slot immediately, same as customer self-cancellation.

### Amendment 2026-08-18 (post-submission, user-directed)

- Change: The phone number field is removed from the booking form entirely.
  Customers now provide only their name (required) and, optionally, an
  email address. There is no longer any required contact field beyond
  name. Requested directly by the project owner to reduce friction in the
  booking form; the tradeoff (the business has no way to reach a customer
  who doesn't supply an email) was flagged and accepted as a deliberate
  choice.
- Change: The booking page now uses a two-step flow — a month calendar to
  pick a day, then a list of that day's open times — instead of a single
  scrolling list of all days at once. Same underlying slots and business
  rules; this only changes how they're presented.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Book an available appointment (Priority: P1)

A customer visits the booking page, sees which slots are still open over the
next several weeks, picks a day, then a time, enters their name (email
optional), and confirms. They immediately see a confirmation and a link
they can use later to cancel.

**Why this priority**: This is the entire reason the system exists. Without
it there is no product.

**Independent Test**: Can be fully tested by opening the booking page with
no prior bookings, selecting an open slot, submitting valid contact details,
and confirming a booking confirmation appears and the slot no longer shows
as available to a second visitor.

**Acceptance Scenarios**:

1. **Given** the booking page with several open slots, **When** a customer
   selects an open slot and submits a valid name, **Then** the booking is
   created, a confirmation with a cancellation link is shown, and that slot
   no longer appears as available.
2. **Given** two customers viewing the same open slot at the same time,
   **When** both submit a booking for that slot within moments of each
   other, **Then** exactly one booking succeeds and the other customer sees
   a clear "this slot was just taken" message with no booking created for
   them.
3. **Given** the booking page, **When** a customer submits the booking form
   with an empty name or an unrecognizable email address, **Then** the
   booking is rejected with a clear, specific validation message and no
   booking is created.

---

### User Story 2 - Owner views and manages upcoming bookings (Priority: P2)

The business owner opens the bookings view, enters the shared passcode, and
sees every upcoming booking with the customer's name, contact info, and
appointment time, so they know their schedule. If a customer calls to
cancel by phone, the owner can cancel that booking directly from this view.

**Why this priority**: Necessary for the business to actually act on the
bookings customers make, but the system still delivers customer value
(User Story 1) even before this exists.

**Independent Test**: Can be fully tested by creating one or more bookings,
then visiting the owner view, entering the correct passcode, and confirming
all bookings appear with correct details and a working cancel action;
entering an incorrect passcode must not reveal any booking data.

**Acceptance Scenarios**:

1. **Given** existing bookings and the correct passcode, **When** the owner
   opens the bookings view and submits the passcode, **Then** all upcoming
   bookings are listed with customer name, contact info, and time.
2. **Given** the bookings view, **When** an incorrect passcode is submitted,
   **Then** no booking data is shown and a generic access-denied message is
   displayed.
3. **Given** an upcoming booking shown in the owner's view, **When** the
   owner cancels it, **Then** the booking is marked cancelled and its slot
   immediately becomes available again on the public booking page.

---

### User Story 3 - Customer cancels their own booking (Priority: P3)

A customer who previously booked a slot opens their private cancellation
link and cancels it, so the slot becomes available to others again.

**Why this priority**: A real convenience and reduces stale/unwanted
bookings, but the system is still viable without it (User Stories 1 and 2
cover the core loop).

**Independent Test**: Can be fully tested by creating a booking, following
its cancellation link, confirming the booking is marked cancelled, and
confirming the slot reappears as available on the booking page immediately
afterward.

**Acceptance Scenarios**:

1. **Given** a confirmed booking and its cancellation link, **When** the
   customer opens the link and confirms cancellation, **Then** the booking
   is cancelled and its slot becomes bookable again right away.
2. **Given** a cancellation link that has already been used (or never
   existed), **When** it is opened again, **Then** the system shows a clear
   message that the link is no longer valid and takes no action.

### Edge Cases

- What happens when two booking attempts for the same slot arrive at
  effectively the same instant? Exactly one MUST succeed; the other MUST
  fail with a clear "no longer available" response, never a duplicate
  booking.
- What happens when a customer tries to book a slot outside business hours,
  in the past, or more than the allowed booking window (30 days) ahead?
  The system MUST reject it with a clear error and MUST NOT offer such
  slots in the first place.
- What happens when the owner passcode is submitted incorrectly multiple
  times? The system MUST keep refusing access without revealing any booking
  data or distinguishing "wrong passcode" from "no bookings exist."
- What happens when a customer submits the booking form with missing or
  malformed required fields? The system MUST reject the submission with a
  specific, understandable message and create no booking.
- What happens at the exact boundary of business hours (e.g., a slot that
  would start right at closing time)? Only slots that fit entirely within
  business hours are ever offered.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display all appointment slots within business
  hours (Monday-Friday, 9 AM-5 PM) and the active booking window that are
  not currently booked.
- **FR-002**: System MUST allow a customer to book any currently-available
  slot by providing their name (email optional), with no account or login
  of any kind.
- **FR-003**: System MUST guarantee that a slot is never held by more than
  one active booking at a time, including when booking requests for the
  same slot arrive concurrently.
- **FR-004**: System MUST show the customer a confirmation immediately after
  a successful booking, including a private, unguessable link they can use
  to cancel it later.
- **FR-005**: System MUST allow a customer to cancel their own booking via
  their private cancellation link, and MUST make the freed slot bookable
  again immediately.
- **FR-006**: System MUST allow the business owner to view all upcoming
  bookings, including customer name and contact info, only after providing
  a correct shared passcode.
- **FR-007**: System MUST reject booking attempts for slots that are in the
  past, outside business hours, or already booked, with a clear error
  message identifying the reason.
- **FR-008**: System MUST validate customer-submitted booking details
  (name required; email, if provided, must be a recognizable shape) and
  reject invalid submissions with an understandable, field-specific error.
- **FR-009**: System MUST NOT require or offer customer accounts, login, or
  passwords anywhere in the booking flow.
- **FR-010**: System MUST NOT reveal any booking or customer data to anyone
  who has not provided the correct owner passcode.
- **FR-011**: System MUST allow the business owner, after providing the
  correct passcode, to cancel any upcoming booking directly from the
  owner's view, immediately freeing that slot.

### Key Entities *(include if feature involves data)*

- **Appointment Slot**: A fixed-length (30-minute) time window that falls
  within business hours. At any moment it is either open or held by exactly
  one active booking.
- **Booking**: A customer's reservation of one slot. Holds the customer's
  name (email optional), the reserved slot's time, when the booking was
  made, its status (active or cancelled), and a unique, unguessable
  cancellation token.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A customer can go from opening the booking page to seeing a
  booking confirmation in under 1 minute for a slot they've already chosen.
- **SC-002**: When multiple booking requests target the same slot at
  effectively the same time, exactly one succeeds every time — verified by
  repeated automated concurrency testing with zero observed double-bookings.
- **SC-003**: A cancelled slot is available for a new booking within 1
  second of the cancellation being confirmed.
- **SC-004**: The owner can see the full current list of upcoming bookings
  within two steps of opening the bookings view (enter passcode, view list).
- **SC-005**: 100% of booking submissions with invalid or missing required
  fields are rejected with a specific, understandable error rather than a
  crash, a silent failure, or a partially-created booking.

## Assumptions

- Single physical service, single provider, single calendar — matching the
  handwritten spec's explicit scope.
- Business hours are fixed at Monday-Friday, 9 AM-5 PM, configurable in one
  place in the code/config rather than through an admin UI.
- Every appointment is the same fixed length: 30 minutes.
- Customers can book any open slot up to 30 days in advance; slots further
  out are simply not generated/shown yet.
- A single timezone is assumed throughout (the server's local time); there
  is no multi-timezone support.
- The owner is authenticated by a single shared passcode read from
  configuration, not a full account system — acceptable given there is only
  one owner and no requirement for individual owner accounts.
- No email/SMS delivery is required or built; the cancellation link is
  surfaced directly on the confirmation page.
