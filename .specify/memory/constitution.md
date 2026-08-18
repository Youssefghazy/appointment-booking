<!--
Sync Impact Report
- Version change: template → 1.0.0
- List of modified principles: n/a (initial ratification)
- Added sections: Core Principles (I–V), Technology Constraints, Development
  Workflow, Governance
- Removed sections: none
- Follow-up TODOs: none
-->

# Appointment Booking System Constitution

## Core Principles

### I. Simplicity First (YAGNI)

The system MUST stay exactly as small as the spec requires: one fixed
service, one calendar, no user accounts. New features, abstractions,
libraries, or services MUST NOT be added unless the current spec explicitly
requires them. When in doubt, prefer the boring, obvious solution over a
clever or "future-proof" one. Rationale: this is a beginner-scoped homework
project; unnecessary complexity increases the chance of bugs and makes the
code harder for the author to explain and defend.

### II. No Double-Booking (NON-NEGOTIABLE)

A slot MUST never be assigned to two bookings, including when two booking
requests arrive at nearly the same instant. This guarantee MUST be enforced
at the database/backend layer (e.g. a unique constraint plus a transaction,
or an equivalent atomic operation) — never solely in the UI or in
application-level logic that reads-then-writes without protection.
Cancelling a booking MUST immediately make its slot bookable again.
Rationale: this is the single most important requirement in the spec; a
race condition here defeats the purpose of the whole system.

### III. Test-First for Critical Paths

The booking flow and, above all, the no-double-booking guarantee MUST have
automated tests, including a test that fires concurrent booking attempts at
the same slot and asserts exactly one succeeds. Tests for a behavior MUST
exist before that behavior is considered done. Rationale: "no double
booking" is a claim that can only be trusted if it's continuously verified,
not just eyeballed once.

### IV. Beginner-Readable Code

Code MUST favor clarity over cleverness: descriptive names, small
functions, minimal indirection, and comments where the "why" isn't obvious.
The author (a beginner) MUST be able to explain every file in the project.
Rationale: the student needs to be able to answer questions about this code
afterward; unreadable code defeats the purpose of the exercise.

### V. Clean, Secret-Free Repository

No credentials, API keys, `.env` files with real secrets, virtual
environments, dependency caches, or private test data may be committed.
Configuration that varies per environment (e.g. the owner's admin
passcode) MUST be read from an environment variable with a documented
example file (`.env.example`), never hardcoded. Rationale: the repository
must be safe to make public, as the assignment requires.

## Technology Constraints

The stack MUST remain simple and beginner-friendly and MUST run entirely
locally with no paid or external services: no payment gateways, no
third-party email/SMS providers, no cloud databases. A file-based or
embedded database (such as SQLite) is preferred over running a separate
database server, since it has no setup cost and still supports the atomic
operations Principle II requires. The chosen web framework MUST have
first-class support for defining a uniqueness constraint at the database
level and running a booking write inside a transaction. Frontend tooling
MUST stay minimal (server-rendered pages or a small script) — no build
pipeline is required for a project this size.

## Development Workflow

This project MUST follow the Spec Kit pipeline in order: constitution →
specify → clarify → plan → tasks → implement, with `analyze` run before
`implement` to catch inconsistencies between the spec, plan, and tasks.
Each pipeline stage's output MUST be committed to git as its own commit
before moving to the next stage, so the project history shows genuine
incremental progress rather than one large dump. The final submission MUST
include a README with setup, running, and testing instructions clear
enough for someone with no prior context to follow.

## Governance

This constitution supersedes ad hoc technical decisions made elsewhere in
the project. Any amendment MUST update this file and bump the version
below according to semantic versioning: MAJOR for removing or redefining a
principle, MINOR for adding a principle or materially expanding guidance,
PATCH for wording/clarification fixes. Before the `implement` stage, the
plan and tasks MUST be checked against these principles (via
`/speckit-analyze` or manual review); unresolved conflicts MUST be fixed
before writing application code.

**Version**: 1.0.0 | **Ratified**: 2026-08-18 | **Last Amended**: 2026-08-18
