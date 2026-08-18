# Specification Analysis Report (`/speckit-analyze`)

Run after `/speckit-tasks`, before `/speckit-implement`, per the constitution's
Development Workflow section.

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F1 | Inconsistency | CRITICAL | tasks.md (old T027, old T033) | Phase 4 (US2) task "owner cancels a booking" called `booking_service.cancel_booking()`, but that function was only implemented later, in Phase 5 (US3). Executing tasks in phase order would fail at Phase 4. | Move the shared `cancel_booking()` implementation into Phase 4 (US2), since US2 has the earlier priority (P2 vs P3) and both stories need it (Spec Kit rule: shared logic → earliest consuming story). Phase 5 (US3) then only adds the customer-facing route/template that call the already-implemented function. |
| F2 | Coverage Gap | MEDIUM | spec.md FR-007; tasks.md Phase 3 | FR-007 (reject bookings outside business hours / in the past) had implementation coverage (T007, old T015) but no dedicated test task — only booked-slot conflicts were tested (via the double-booking tests). | Add an explicit test task for booking rejection on out-of-hours/past slot attempts. |
| F3 | Inconsistency | LOW | tasks.md "Recommended order" note | The Implementation Strategy / Dependencies text suggested optionally doing US3 (Phase 5) before US2 (Phase 4), which contradicts F1's fix (Phase 5 now depends on Phase 4's shared `cancel_booking`). | Remove the swap suggestion; state the phases run strictly in order 1→2→3→4→5→6. |
| F4 | Underspecification | LOW | spec.md SC-005 / tasks.md T012 | SC-005 claims 100% of invalid submissions are rejected, but the original test task only mentioned name/phone, not the optional email field's format check (data-model.md rule 4). | Broaden the existing invalid-input test task's description to also cover a malformed email, rather than adding a whole new task. |

**Coverage Summary Table** (functional requirements → tasks, post-fix):

| Requirement | Has Task? | Task IDs (post-fix numbering) | Notes |
|---|---|---|---|
| FR-001 | Yes | T007, T017 | |
| FR-002 | Yes | T016, T018 | |
| FR-003 (no double-booking) | Yes | T014, T015, T016 | Constitution Principle II — highest scrutiny |
| FR-004 | Yes | T016, T020 | |
| FR-005 | Yes | T025, T033, T034, T036 | |
| FR-006 | Yes | T023, T026, T027 | |
| FR-007 | Yes (after fix) | T013, T007, T016 | Was gap F2, now covered |
| FR-008 | Yes | T012 | |
| FR-009 (no accounts) | N/A by omission | — | Satisfied by not building any account system; no task needed |
| FR-010 | Yes | T023 | |
| FR-011 | Yes | T024, T025, T029 | |

**Constitution Alignment Issues**: None remaining after F1 is fixed. Before
the fix, F1 was itself a de facto Principle III violation risk (a task
sequence that cannot actually be executed test-first, since Phase 4's
implementation would fail immediately).

**Unmapped Tasks**: None — every implementation task maps to at least one
FR, and every test task maps to a user story's acceptance scenario.

**Metrics**:

- Total Functional Requirements: 11
- Total Tasks (post-fix): 41
- Coverage: 11/11 requirements have ≥1 task (100%)
- Ambiguity Count: 0 vague/unquantified adjectives found
- Duplication Count: 0
- Critical Issues Count: 1 (F1 — fixed in this same commit)

## Next Actions

F1 (CRITICAL) has been fixed directly in `tasks.md` in this same commit,
since it was a structural task-ordering bug rather than a product decision
— no reason to leave it broken and ask separately. F2 and F3 are also
applied. F4 was folded into the existing test task's description rather
than adding a new task, keeping the task count minimal per Constitution
Principle I.

Proceeding to `/speckit-implement` is safe now that F1 is resolved.
