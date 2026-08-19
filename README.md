# Appointment Booking System

A small web app for booking a single fixed service against one calendar —
no user accounts, one business, one schedule. Built as a homework project
following the [GitHub Spec Kit](https://github.com/github/spec-kit)
spec-driven workflow: constitution → spec → clarify → plan → tasks →
implement → analyze.

## What it does

- Customers pick a day, then a time on that day, then book it by giving
  just their name (email optional) — no account needed.
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
├── logging_config.py  Structured JSON logging setup
├── observability.py   Optional Langfuse tracing (no-op if unconfigured)
├── templates/          HTML pages (Jinja2)
└── static/             CSS

tests/               Automated tests (pytest)
├── test_booking_flow.py     Booking a slot + input validation
├── test_booking_stages.py   The booking page's day/time/details progressive disclosure
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

## Observability

The app has two independent layers of observability, both off by default
in the sense that neither requires you to change any code -- only the
second one needs any setup at all.

**Structured JSON logs (always on).** Every HTTP request logs one JSON
line (method, path, status code, how long it took), and every meaningful
business event -- a booking created, a booking rejected and why, a
cancellation, an owner login attempt -- logs its own JSON line too. These
print straight to the terminal (`stdout`), which is exactly what a host
like Render collects as your service's log stream, so there's nothing
extra to configure. A booking looks like this in the logs:

```json
{"timestamp": "2026-08-19T14:03:11+00:00", "level": "INFO", "logger": "app", "message": "booking_created", "slot_start": "2026-08-19T14:00:00", "booking_id": 1}
```

None of these events ever include a customer's name or email -- only
non-personal fields like the slot time, a booking id, or a success/fail
reason.

**Langfuse tracing (optional).** [Langfuse](https://langfuse.com) is
built for tracing LLM/agent calls, which this app doesn't make -- but it
also works as a general tracing backend, so the same business events
above are also sent there as spans, *if* you've configured it, giving you
a searchable dashboard instead of raw log lines. To turn it on:

1. Create a free account at [Langfuse Cloud](https://langfuse.com/pricing)
   (the Hobby plan is free, no card required) and create a project.
2. Copy that project's public key and secret key.
3. Set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (and optionally
   `LANGFUSE_HOST`, if not using Langfuse Cloud) in `.env` locally, or as
   environment variables on your host.

Leave those unset and `app/observability.py` quietly does nothing --
nothing else about the app changes or breaks.

## Deploying

The app is a normal FastAPI service, so it deploys the same way most
small Python web apps do. A `render.yaml` is included for
[Render](https://render.com)'s free tier:

1. Push this repo to GitHub (already done if you're reading this from
   the repo).
2. On [Render](https://dashboard.render.com), **New +** → **Blueprint**,
   and point it at this repository. Render reads `render.yaml`
   automatically and fills in the build/start commands.
3. When prompted, set `OWNER_PASSCODE` (required, no default). Leave the
   `LANGFUSE_*` variables unset unless you've set up Langfuse (see
   above).
4. Deploy. Render gives you a public `https://<your-service>.onrender.com`
   URL. `GET /healthz` returns `{"status": "ok"}` and is a good way to
   confirm the deploy actually came up.

Two free-tier things worth knowing about, so nothing looks "broken" when
it's actually just how the free tier works:

- **Spin-down.** A free Render service spins down after 15 minutes with
  no traffic, and takes about a minute to spin back up on the next
  request -- the first visit after a quiet period will just look slow to
  load, not down.
- **Ephemeral disk.** Render's free tier doesn't persist the filesystem
  across restarts/redeploys, and this app stores its data in a SQLite
  *file* (`data/booking.db`). That means every time the free service
  restarts (including a spin-down/spin-up cycle), **all bookings in it
  are wiped** and it starts from an empty database again. That's fine for
  demoing the app or for this assignment, but it is not how you'd run
  this for a real business -- that would need either a paid Render disk
  or a hosted database instead of a local SQLite file.

## Notes on scope

Per the assignment, this is deliberately small: one service, one calendar,
no payments, no multiple staff, no SMS/email integrations, and no customer
accounts anywhere. See `spec.md` and `CLARIFICATIONS.md` for the original
handwritten spec and the decisions made to fill in what it left open, and
`specs/001-appointment-booking/spec.md` for the full formal specification
those decisions were built into.
