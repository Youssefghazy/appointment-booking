# Appointment Booking System

A small web app for booking a single fixed service against one calendar —
no user accounts, one business, one schedule. Built as a homework project
following the [GitHub Spec Kit](https://github.com/github/spec-kit)
spec-driven workflow: constitution → spec → clarify → plan → tasks →
implement → analyze.

## What it does

- Customers can see which appointment slots are open and book one, giving
  just their name and phone number — no account needed.
- A slot can never be double-booked, **even if two people try to book it
  at the exact same moment.** This is enforced by the database itself (a
  partial unique index + transaction), not just by the page.
- After booking, a customer gets a private link they can use to cancel
  their own appointment later, which immediately frees the slot again.
- The business owner can see all upcoming bookings — and cancel any of
  them — behind a single shared passcode (there's no owner account system
  either, just one passcode).

## Project layout

```text
app/                 The application
├── main.py            FastAPI routes (the web layer)
├── booking_service.py Business logic: list slots, book, cancel
├── db.py              SQLite connection + schema
├── config.py          Reads settings from environment variables
├── templates/          HTML pages (Jinja2)
└── static/             CSS

tests/               Automated tests (pytest)
├── test_booking_flow.py     Booking a slot + input validation
├── test_double_booking.py   The no-double-booking guarantee, under real concurrency
├── test_owner_view.py       Owner passcode gate
└── test_cancellation.py     Owner cancel + customer self-cancel

spec.md               The original handwritten spec (written by hand, no AI)
CLARIFICATIONS.md      The "what's underspecified here?" exercise and answers
specs/001-appointment-booking/   Every Spec Kit pipeline artifact:
├── spec.md             Formal specification
├── plan.md             Technical plan (stack, architecture, constitution check)
├── research.md          Design decisions and why they were made
├── data-model.md         The Booking entity and its rules
├── contracts/            HTTP endpoint contracts
├── tasks.md              The full task breakdown (all 41 tasks, done)
├── analysis-report.md    Cross-artifact consistency check
└── checklists/            Spec quality checklist
.specify/memory/constitution.md   The project's own ground rules
```

## Requirements

- Python 3.11 or newer

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set `OWNER_PASSCODE` to whatever passcode you want the
business owner to use — it's the only thing you must configure. The app
will refuse to start without it.

## Running it

```bash
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/** in a browser. Visit
**http://127.0.0.1:8000/owner** and enter your `OWNER_PASSCODE` to see the
owner's view of bookings.

The database is a single SQLite file created automatically at
`data/booking.db` the first time you run the app. Delete that file any
time to start with a clean slate.

## Running the tests

```bash
pytest
```

This runs the full automated test suite, including
`tests/test_double_booking.py`, which fires many concurrent booking
requests at the same slot from real threads and asserts that exactly one
of them succeeds — the automated proof that the no-double-booking rule
actually holds, not just something claimed in the docs.

## How "no double-booking" actually works

This is the one rule the whole assignment centers on, so it's worth
explaining plainly. In `app/db.py`, the bookings table has this index:

```sql
CREATE UNIQUE INDEX idx_one_active_booking_per_slot
ON bookings (slot_start)
WHERE status = 'active';
```

That tells SQLite itself: "there can only ever be one row with
`status = 'active'` for any given `slot_start`." When `app/booking_service.py`
tries to insert a new booking, it does so inside an explicit transaction
(`BEGIN IMMEDIATE`). If two people try to book the same slot at nearly the
same instant, SQLite serializes the two attempts — one insert succeeds,
and the second one is rejected by the database with a uniqueness error,
which the code turns into a friendly "sorry, that slot was just taken"
message. The check was never "look at the list, then decide" in
application code (which is the classic bug that causes double-booking) —
it's the database refusing the conflicting row, which is reliable even
under a genuine race.

Cancelling a booking just flips its `status` to `'cancelled'`, which drops
it out of that unique index, so the slot is immediately available again.

## Notes on scope

Per the assignment, this is deliberately small: one service, one calendar,
no payments, no multiple staff, no SMS/email integrations, and no customer
accounts anywhere. See `spec.md` and `CLARIFICATIONS.md` for the original
handwritten spec and the decisions made to fill in what it left open, and
`specs/001-appointment-booking/spec.md` for the full formal specification
those decisions were built into.
