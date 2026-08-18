# Implementation Plan: Single-Service Appointment Booking

**Branch**: `001-appointment-booking` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-appointment-booking/spec.md`

## Summary

Build a small, server-rendered web app for booking a single fixed service
against one calendar, with no customer accounts. The primary technical risk
is Principle II of the constitution — no double-booking, enforced reliably
even under concurrent requests. The approach: SQLite as the single source of
truth, with a partial UNIQUE index that only allows one *active* booking per
slot start time, and every booking write wrapped in an immediate
transaction. The database itself rejects a conflicting write; the
application never relies on "check then insert" logic alone.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI (web framework + routing), Uvicorn (ASGI
server), Jinja2 (server-rendered HTML templates), python-dotenv (load
`OWNER_PASSCODE` from `.env`). No ORM — the SQLite schema and queries are
simple enough to write directly with Python's built-in `sqlite3` module,
which keeps the data layer transparent and easy for a beginner to read and
reason about (Constitution Principle IV).

**Storage**: SQLite, single file (`data/booking.db`), accessed via the
standard library `sqlite3` module. Chosen per the constitution's Technology
Constraints: zero setup cost, runs locally, and supports the transactional
+ unique-constraint guarantee Principle II requires.

**Testing**: pytest, plus FastAPI's `TestClient` (built on httpx) for
HTTP-level tests. The double-booking guarantee is tested two ways: (1)
directly against the booking function using real OS threads and a real
on-disk database file, to exercise the actual SQLite locking/constraint
behavior under a genuine race; (2) at the HTTP layer with concurrent
requests through `TestClient`, as a second, more end-to-end check.

**Target Platform**: Linux server (also runs on macOS/Windows for local
development); no OS-specific dependencies.

**Project Type**: Single web service (server-rendered, no separate frontend
build).

**Performance Goals**: Not a scale-sensitive project (single business,
single calendar). Success criteria in the spec (SC-001, SC-003) are about
responsiveness for one user at a time, not throughput — normal local HTTP
response times (well under 1 second) are sufficient.

**Constraints**: Must run entirely offline/locally with no paid services
(Constitution: Technology Constraints). No customer accounts anywhere
(spec FR-009).

**Scale/Scope**: One service, one calendar, a handful of bookings per day.
No multi-tenancy, no horizontal scaling needs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Simplicity First**: PASS. One FastAPI app, one SQLite file, no ORM,
  no build step for the frontend, no extra services.
- **II. No Double-Booking (NON-NEGOTIABLE)**: PASS (design-level). Enforced
  via a partial UNIQUE index (`WHERE status = 'active'`) on the booking's
  slot start time, combined with an immediate SQLite transaction around the
  insert and a caught `IntegrityError` mapped to a clear "already booked"
  response. This is a database-level guarantee, not a UI-level check.
- **III. Test-First for Critical Paths**: PASS (planned). Concurrency test
  for double-booking and booking-flow tests are part of `tasks.md` before
  the corresponding implementation tasks are marked done.
- **IV. Beginner-Readable Code**: PASS. Raw SQL via `sqlite3` instead of an
  ORM, small single-purpose modules, no framework magic beyond FastAPI's
  routing/templating.
- **V. Clean, Secret-Free Repository**: PASS (planned). `OWNER_PASSCODE`
  read from an environment variable via `.env` (gitignored), with
  `.env.example` documenting it. `data/booking.db` is also gitignored.

No violations — Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-appointment-booking/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py            # FastAPI app + route handlers
├── db.py              # SQLite connection, schema creation
├── booking_service.py # Business logic: list slots, book, cancel
├── config.py          # Reads OWNER_PASSCODE, business-hours settings from env
├── templates/
│   ├── base.html
│   ├── booking.html       # Customer: view + book slots
│   ├── confirmation.html  # Customer: booking confirmed + cancel link
│   ├── cancel.html        # Customer: cancellation result
│   ├── owner_login.html   # Owner: passcode form
│   └── owner_bookings.html# Owner: booking list + cancel action
└── static/
    └── style.css

tests/
├── conftest.py
├── test_booking_flow.py     # User Story 1: view + book + validation
├── test_double_booking.py   # Principle II: concurrency guarantee
├── test_cancellation.py     # User Story 3 + owner cancel (FR-005, FR-011)
└── test_owner_view.py       # User Story 2: passcode gate + listing

data/                    # gitignored; holds booking.db at runtime
requirements.txt
.env.example
```

**Structure Decision**: Single project (Option 1) — this is one small web
service with server-rendered pages, not a separate frontend/backend split.
No `src/` nesting beyond `app/`, since the whole app is one deployable unit.

## Complexity Tracking

Not applicable — no constitution violations.
