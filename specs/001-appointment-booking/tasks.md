# Tasks: Single-Service Appointment Booking

**Input**: Design documents from `/specs/001-appointment-booking/`
**Tests**: Included and REQUIRED — Constitution Principle III ("Test-First for
Critical Paths") and the assignment both require automated tests, especially
for the no-double-booking guarantee.

**Organization**: Tasks are grouped by user story (from spec.md) so each
story is independently completable and testable.

## Phase 1: Setup (project initialization)

- [ ] T001 Create project directories per plan.md: `app/`, `app/templates/`, `app/static/`, `tests/`, `data/` (with `app/__init__.py`)
- [ ] T002 [P] Create `requirements.txt` with fastapi, uvicorn, jinja2, python-multipart, python-dotenv, itsdangerous, pytest, httpx
- [ ] T003 [P] Create `.env.example` documenting `OWNER_PASSCODE` (and optional overrides for business hours/slot length)
- [ ] T004 [P] Create `.gitignore` covering `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `data/*.db`, `.pytest_cache/`

## Phase 2: Foundational (blocking prerequisites for all user stories)

**⚠️ No user story work can start until this phase is complete.**

- [ ] T005 Implement `app/config.py`: read `OWNER_PASSCODE` (required, no default), `BUSINESS_START_HOUR`, `BUSINESS_END_HOUR`, `BUSINESS_DAYS`, `SLOT_MINUTES`, `BOOKING_WINDOW_DAYS` from environment with sensible defaults (9, 17, Mon-Fri, 30, 30)
- [ ] T006 Implement `app/db.py`: sqlite3 connection helper (`get_connection()`), `init_db()` that creates the `bookings` table and the partial unique indexes from data-model.md (`idx_one_active_booking_per_slot`, unique index on `cancel_token`)
- [ ] T007 Implement slot-computation logic in `app/booking_service.py`: `list_available_slots(conn)` — generate all business-hours slots in the booking window, excluding past times and any `slot_start` with an active booking
- [ ] T008 Set up the FastAPI app skeleton in `app/main.py`: create the `FastAPI()` instance, mount `app/static`, configure `Jinja2Templates`, add `SessionMiddleware` (secret key from `config.py`), call `init_db()` on startup
- [ ] T009 [P] Create `app/templates/base.html` shared layout (nav, minimal styling hook) used by all pages

**Checkpoint**: App boots (`uvicorn app.main:app`) and the database file initializes with the correct schema. No routes are functional yet.

## Phase 3: User Story 1 - Book an available appointment (Priority: P1) 🎯 MVP

**Goal**: A customer can see open slots and book one; a slot can never be double-booked, even under concurrent attempts.

**Independent Test**: Load the booking page with no prior bookings, book an open slot with valid details, confirm the slot disappears from the list and a confirmation with a cancel link appears; fire two concurrent bookings at the same slot and confirm exactly one succeeds.

### Tests for User Story 1 (write first; must fail before implementation)

- [ ] T010 [P] [US1] Write `tests/test_booking_flow.py::test_home_page_lists_available_slots` — `GET /` returns 200 and includes the expected upcoming slots
- [ ] T011 [P] [US1] Write `tests/test_booking_flow.py::test_successful_booking_returns_confirmation` — valid `POST /book` redirects to a confirmation page showing the booked time and a cancel link, and the slot no longer appears on `GET /`
- [ ] T012 [P] [US1] Write `tests/test_booking_flow.py::test_invalid_input_rejected` — empty name / malformed phone via `POST /book` returns a validation error and creates no booking (FR-008)
- [ ] T013 [P] [US1] Write `tests/test_double_booking.py::test_concurrent_service_calls_only_one_succeeds` — spawn real OS threads calling `booking_service.create_booking()` directly for the same `slot_start` against a shared on-disk SQLite file; assert exactly one succeeds and the rest raise `SlotAlreadyBookedError`
- [ ] T014 [P] [US1] Write `tests/test_double_booking.py::test_concurrent_http_requests_only_one_succeeds` — spawn threads issuing `POST /book` for the same slot through `TestClient`; assert exactly one 303 and the rest 409

### Implementation for User Story 1

- [ ] T015 [US1] Implement `booking_service.create_booking(conn, slot_start, name, phone, email)` in `app/booking_service.py`: validate inputs (data-model.md rules), run the insert inside a `BEGIN IMMEDIATE` transaction, generate `cancel_token` via `secrets.token_urlsafe`, catch `sqlite3.IntegrityError` and raise `SlotAlreadyBookedError`
- [ ] T016 [US1] Implement `GET /` route in `app/main.py`, rendering `booking.html` with the result of `list_available_slots`
- [ ] T017 [US1] Implement `POST /book` route in `app/main.py`: parse form fields, call `create_booking`, redirect (303) to `/confirmation/{cancel_token}` on success, re-render `booking.html` with a specific error on validation failure (422) or `SlotAlreadyBookedError` (409)
- [ ] T018 [P] [US1] Create `app/templates/booking.html`: slot list + booking form, error message placeholder
- [ ] T019 [P] [US1] Create `app/templates/confirmation.html`: booked time + cancellation link
- [ ] T020 [US1] Implement `GET /confirmation/{cancel_token}` route: look up the booking by token, render `confirmation.html`, or a 404 page if not found

**Checkpoint**: `pytest tests/test_booking_flow.py tests/test_double_booking.py` passes. This alone is a demoable MVP.

## Phase 4: User Story 2 - Owner views and manages upcoming bookings (Priority: P2)

**Goal**: The owner can see all upcoming bookings behind a shared passcode, and cancel any of them.

**Independent Test**: With bookings created from Phase 3, visit `/owner`, confirm wrong passcode is refused and no data leaks, confirm right passcode shows the bookings, and confirm cancelling one frees its slot.

### Tests for User Story 2

- [ ] T021 [P] [US2] Write `tests/test_owner_view.py::test_owner_bookings_requires_session` — `GET /owner/bookings` without a session redirects to `/owner`
- [ ] T022 [P] [US2] Write `tests/test_owner_view.py::test_passcode_gate` — wrong passcode via `POST /owner` returns 401 with no booking data present in the response; correct passcode grants access and lists existing bookings (FR-006, FR-010)
- [ ] T023 [P] [US2] Write `tests/test_cancellation.py::test_owner_can_cancel_booking` — after authenticating, `POST /owner/bookings/{id}/cancel` frees the slot immediately, verified via `GET /` (FR-011)

### Implementation for User Story 2

- [ ] T024 [US2] Implement owner session helper in `app/main.py` (`require_owner` dependency checking the session cookie set after passcode verification)
- [ ] T025 [US2] Implement `GET /owner` and `POST /owner` routes: render passcode form; on correct passcode (compared against `config.OWNER_PASSCODE`) set the session flag and redirect to `/owner/bookings`
- [ ] T026 [US2] Implement `GET /owner/bookings` route (behind `require_owner`): list all active bookings with a cancel action per row
- [ ] T027 [US2] Implement `POST /owner/bookings/{booking_id}/cancel` route (behind `require_owner`): call `booking_service.cancel_booking(booking_id=..., by="owner")`, redirect back to the list
- [ ] T028 [P] [US2] Create `app/templates/owner_login.html`
- [ ] T029 [P] [US2] Create `app/templates/owner_bookings.html`
- [ ] T030 [US2] Implement `POST /owner/logout` route clearing the session

**Checkpoint**: `pytest tests/test_owner_view.py tests/test_cancellation.py -k owner` passes.

## Phase 5: User Story 3 - Customer cancels their own booking (Priority: P3)

**Goal**: A customer can cancel their own booking via their private link, freeing the slot immediately.

**Independent Test**: Book a slot, follow its cancellation link, confirm cancellation, verify the slot is available again and the same link can't cancel twice.

### Tests for User Story 3

- [ ] T031 [P] [US3] Write `tests/test_cancellation.py::test_customer_can_cancel_via_link` — `POST /cancel/{token}` on an active booking frees the slot immediately (FR-005), verified via `GET /`
- [ ] T032 [P] [US3] Write `tests/test_cancellation.py::test_reusing_cancel_link_is_safe` — a second `POST /cancel/{token}` for an already-cancelled (or unknown) token makes no state change and shows a "no longer valid" result rather than erroring or double-cancelling

### Implementation for User Story 3

- [ ] T033 [US3] Implement `booking_service.cancel_booking(conn, cancel_token=..., by="customer")` in `app/booking_service.py`: sets `status='cancelled'`, `cancelled_at`, `cancelled_by`; no-ops safely if already cancelled or token unknown
- [ ] T034 [US3] Implement `GET /cancel/{cancel_token}` route: side-effect-free confirmation prompt page
- [ ] T035 [US3] Implement `POST /cancel/{cancel_token}` route: performs the cancellation, renders the result
- [ ] T036 [P] [US3] Create `app/templates/cancel.html`

**Checkpoint**: `pytest tests/test_cancellation.py` passes in full.

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Add minimal `app/static/style.css` for readability (no framework)
- [ ] T038 [P] Run `pytest` for the full suite and fix any failures found
- [ ] T039 Manually walk through every scenario in `quickstart.md` against the running app and confirm each one matches
- [ ] T040 Write the top-level `README.md` (setup, run, test instructions) per the assignment requirements

## Dependencies & Execution Order

- **Phase 1 (Setup)** → **Phase 2 (Foundational)**: strictly sequential; Phase 2 blocks every user story.
- **Phase 3 (US1)** depends only on Phase 2. It is the MVP and should be completed and verified first.
- **Phase 4 (US2)** depends on Phase 2 and on bookings existing to view — practically sequenced after Phase 3, though its own routes don't call US1 code directly.
- **Phase 5 (US3)** depends on Phase 2 and the `cancel_token` produced by US1's `create_booking` (Phase 3) — sequenced after Phase 3.
- **Phase 6 (Polish)** runs after all three user stories are implemented and tested.

Recommended order: Phase 1 → Phase 2 → Phase 3 (US1) → Phase 5 (US3, shares `booking_service` cancel logic conceptually with US2) → Phase 4 (US2) → Phase 6. (US2 and US3 could be swapped since they're independent of each other; both only need Phase 2 + US1's booking creation to exist.)

## Parallel Execution Examples

Within Phase 3, T010-T014 (all test-writing tasks) can be done in parallel — they touch only test files. T018 and T019 (templates) can be done in parallel with each other and with T015 (service logic), since they're different files, but T016/T017 (routes) depend on T015 existing.

Within Phase 4, T021-T023 (tests) can run in parallel; T028/T029 (templates) can run in parallel with T024 (session helper).

## Implementation Strategy

**MVP first**: Complete Phase 1 → Phase 2 → Phase 3 (User Story 1) and stop there to get a working, demoable, double-booking-safe booking flow. Phases 4 and 5 add the owner view and self-service cancellation on top, each independently testable and shippable.
