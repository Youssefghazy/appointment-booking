# Phase 1 Data Model: Single-Service Appointment Booking

## Entity: Booking

The only persisted entity. Appointment "slots" are not stored as rows —
they're computed at request time from the business-hours configuration
(Monday–Friday, 9 AM–5 PM, 30-minute increments, up to 30 days ahead) minus
whichever slot start times already have an active `Booking`.

| Field | Type | Constraints / Notes |
|---|---|---|
| `id` | INTEGER | Primary key, autoincrement. |
| `slot_start` | TEXT (ISO 8601 datetime, e.g. `2026-08-19T09:00:00`) | Required. Must fall within business hours and the booking window (validated in the service layer before insert). |
| `customer_name` | TEXT | Required, non-empty after trimming whitespace. |
| `customer_phone` | TEXT | Required. Validated as a plausible phone number (digits, spaces, `+`, `-`, min length) — not full E.164 validation, just enough to reject obvious junk (spec FR-008). |
| `customer_email` | TEXT | Optional. If present, validated as a plausible email shape. |
| `status` | TEXT | `'active'` or `'cancelled'`. Defaults to `'active'`. |
| `cancel_token` | TEXT | Required, unique. A random URL-safe token (`secrets.token_urlsafe(24)`) generated at booking time; used in the cancellation link so it can't be guessed or enumerated (spec FR-005, Edge Cases). |
| `created_at` | TEXT (ISO 8601 datetime) | Set by the server at insert time. |
| `cancelled_at` | TEXT (ISO 8601 datetime) | NULL unless `status = 'cancelled'`. |
| `cancelled_by` | TEXT | `'customer'` or `'owner'`, set when `status` becomes `'cancelled'`. Recorded for clarity/debugging, not shown to other customers. |

### Constraints

- **Primary key**: `id`.
- **Uniqueness (the core guarantee)**: a partial unique index ensures at
  most one row with a given `slot_start` can have `status = 'active'` at
  any time:

  ```sql
  CREATE UNIQUE INDEX idx_one_active_booking_per_slot
  ON bookings (slot_start)
  WHERE status = 'active';
  ```

- **Uniqueness**: `cancel_token` has its own unique index so a token can
  reliably identify exactly one booking.

### State transitions

```
        book (insert, status='active')
[ no row ] ─────────────────────────────► [ active ]
                                               │
                          cancel (customer link or owner action)
                                               ▼
                                         [ cancelled ]
```

- `active → cancelled`: allowed once, via customer cancellation link or
  owner cancel action. Sets `cancelled_at` and `cancelled_by`.
- `cancelled → active`: never happens. A customer who wants the same slot
  again after cancelling makes a brand-new booking (new row), which the
  partial unique index freely allows since the old row is no longer
  `active`.
- There is no `active → active` transition (no editing a booking's time —
  out of scope per the handwritten spec).

### Validation rules (enforced in `booking_service.py` before any write)

1. `slot_start` must be one of the currently valid computed slots (within
   business hours, within the 30-day window, not in the past).
2. `customer_name` must be non-empty after trimming.
3. `customer_phone` must match a permissive pattern requiring at least 7
   digits, allowing leading `+`, spaces, dashes, and parentheses.
4. `customer_email`, if provided, must contain exactly one `@` with
   non-empty text on both sides.
5. On insert, if the partial unique index rejects the write
   (`sqlite3.IntegrityError`), the service raises a domain-specific
   `SlotAlreadyBookedError`, which the route layer turns into a 409
   response with a clear message — this is the enforcement point for
   Constitution Principle II.
