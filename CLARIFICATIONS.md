# Clarification Exercise: "What's Underspecified Here?"

This document records the required homework step 02: asking the agent what's
underspecified in the handwritten `spec.md`, then answering it. This happened
*after* `spec.md` was committed on its own, and *before* any Spec Kit stage
ran.

## Gaps identified in the handwritten spec.md

1. **Owner access without accounts** — the spec says the owner can view all
   future bookings, but the app has no accounts anywhere. Nothing specified
   how the booking list (containing customer names and phone numbers) stays
   private from the general public.
2. **Business hours** — the spec says the business has "restricted
   hours/days" but never states what they are.
3. **Slot length** — "one fixed length of appointment" is stated, but the
   actual duration isn't given.
4. **Cancellation** — the "what the owner can do" section implies a customer
   might cancel their own booking ("unless there is a customer calling to
   cancel it"), but this was never confirmed as an actual feature.

## Decisions (answered by the student)

| Question | Decision |
|---|---|
| How is the owner's bookings view protected, given there are no accounts? | Simple shared password. The owner enters one passcode to see the bookings page. |
| Business hours | Monday–Friday, 9 AM–5 PM. |
| Slot length | 30 minutes. |
| Can customers cancel their own booking? | Yes, via a private cancellation link shown after booking (no login needed). Cancelling **must** immediately free the slot so it becomes bookable again. |

## Minor technical details resolved by the agent (not meaningful product decisions)

- **Required contact fields**: name (required) + phone (required); email
  optional. Keeps the form simple while still giving the owner a way to
  reach the customer.
- **Booking window**: customers can book any open slot within the next 30
  days. Slots further out simply aren't generated/shown yet.
- **Timezone**: single timezone, matching the server's local time. No
  multi-timezone support (single physical business, single location).
- **Slot generation**: slots are derived from the fixed business hours +
  slot length, minus whatever is already booked or cancelled — not stored
  as individually pre-created rows for all eternity, generated for the
  active booking window.
- **Past slots**: any slot whose start time has already passed is never
  shown as available, regardless of booking status.
- **Cancellation link format**: a random, unguessable token (not a
  sequential/booking ID) so a cancellation link can't be brute-forced to
  cancel someone else's booking.
