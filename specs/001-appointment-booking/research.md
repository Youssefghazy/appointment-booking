# Phase 0 Research: Single-Service Appointment Booking

No `[NEEDS CLARIFICATION]` markers remained in the Technical Context after
the clarification exercise, so this phase focuses on validating the
technical approach rather than resolving open unknowns.

## Decision: Enforce no-double-booking with a partial UNIQUE index + transaction

**Decision**: Store bookings in a single `bookings` table with a
`slot_start` column (ISO 8601 datetime string) and a `status` column
(`'active'` or `'cancelled'`). Create a partial unique index:

```sql
CREATE UNIQUE INDEX idx_one_active_booking_per_slot
ON bookings (slot_start)
WHERE status = 'active';
```

Every booking write runs inside an explicit `BEGIN IMMEDIATE` transaction,
and the application catches `sqlite3.IntegrityError` raised by the unique
index violation, translating it into a clear "slot already booked" response
instead of letting it crash the request.

**Rationale**: This pushes the no-double-booking guarantee down to the
database engine itself, which is the only place that can atomically decide
"is this the first active booking for this slot?" when two requests arrive
at nearly the same time. `BEGIN IMMEDIATE` acquires SQLite's write lock up
front, so two concurrent booking attempts for the same slot are strictly
serialized: the second one to reach the insert always fails the unique
constraint, deterministically, no matter how close in time the two requests
were. Cancelling a booking simply updates its `status` to `'cancelled'`,
which removes it from the partial index and immediately makes the slot
available again (Assumption/FR-005/FR-011).

**Alternatives considered**:
- *Application-level "check if booked, then insert" without a DB
  constraint*: rejected — this is exactly the race condition the spec
  forbids (FR-003); two concurrent checks can both see "available" before
  either insert happens.
- *A separate `slots` table pre-populated with every future slot, booked via
  an UPDATE with `WHERE status = 'open'`*: workable, but adds a background
  job to keep slots pre-generated and a migration step every time business
  hours change. Rejected in favor of computing slots on the fly from
  business-hours configuration, which is simpler (Constitution Principle I)
  and still fully compatible with the same unique-index guarantee, since
  the guarantee lives on the `bookings` table either way.
- *PostgreSQL with row-level locking / `SELECT ... FOR UPDATE`*: rejected as
  unnecessary complexity and an extra service to install/run for a
  single-user, low-volume project (Constitution: Technology Constraints).

## Decision: FastAPI + Jinja2 server-rendered pages, no separate frontend

**Decision**: Use FastAPI to serve both the HTML pages (via Jinja2
templates) and handle form submissions (POST) directly, rather than
building a separate JSON API consumed by a JavaScript frontend.

**Rationale**: There is no requirement for a rich interactive UI — the spec
describes simple list-and-submit flows. Server-rendered HTML avoids a
frontend build step/toolchain entirely, which keeps the project small and
easy for a beginner to run (`uvicorn app.main:app`) and understand end to
end (Constitution Principle I & IV).

**Alternatives considered**:
- *React/Vue SPA + separate API*: rejected as unnecessary complexity for
  three simple pages and a form.
- *Flask instead of FastAPI*: both are reasonable; FastAPI was chosen for
  its built-in request validation (via Pydantic) for the booking form,
  automatic `/docs` endpoint (useful for the student to inspect and explain
  the API later), and because it matches technology the internship
  curriculum has already introduced.

## Decision: Owner authentication via a single shared passcode, no sessions library

**Decision**: The owner submits a passcode via a POST form; on success the
server sets a short-lived, signed cookie (using Starlette's built-in
`SessionMiddleware`, already bundled with FastAPI's dependencies) so the
owner doesn't have to re-enter the passcode on every request during one
browsing session.

**Rationale**: Meets the clarification answer (a simple shared password)
without building a user/account system, and `SessionMiddleware` is a single
line of setup rather than a new dependency.

**Alternatives considered**:
- *HTTP Basic Auth*: simpler, but no proper "log out" and awkward browser
  UX for a demo project. Rejected in favor of the small session cookie.
- *Full account system (username/password per owner)*: explicitly out of
  scope — there is only one owner and the spec forbids accounts generally.
