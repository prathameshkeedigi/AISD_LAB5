# TalentHub Placement Portal – Current Status and SDLC/TDD Plan

**Project:** `talenthub-placement-portal` (cloned into `Lab5/talenthub-placement-portal`)
**Repository:** https://github.com/kachavimathamit/talenthub-placement-portal (branch `master`, 2 commits, both dated 5 Nov 2026)
**Written:** 6 Nov 2026, 13:58
**Measured against:** `TalentHub_Reference/TalentHub_Requirements_v2.docx` (FR/NFR IDs below) and our Lab 4 schema (`Lab4_TalentHub_Data_Design/ai_outputs/TalentHub_Normalized_Schema.md`)

> **Status of this document:** this is a plan only. No project code has been changed and no packages have been installed. Section 6 lists the decisions the team must make before any code is written.

---

## Part 1 – Current status

### 1.1 What the project is
TalentHub is a web app for running a college placement season. Students apply to company job listings, companies shortlist and interview students and issue offers, students accept or decline, and the placement coordinator views statistics.

### 1.2 What exists today

| Area | What is there |
|---|---|
| **Backend** | Python FastAPI app in `backend/`, about 1,000 lines of code |
| **Layers** | `api/` (routers) → `services/` → `repositories/` → `models/`, plus `schemas/` (Pydantic) and `core/` (database, JWT) |
| **Database** | SQLite through async SQLAlchemy (`talenthub.db`). Tables are created at startup with `create_all`; there are no migrations |
| **Tables (7)** | `users`, `students`, `companies`, `job_listings`, `applications`, `interviews`, `offers` |
| **Auth** | JWT login (`/auth/login`), bcrypt password hashes, role check with `require_role(...)`. Roles are `STUDENT`, `COMPANY` and `COORDINATOR` |
| **Endpoints** | Login; list/create jobs; apply; my applications; company applicants; shortlist/reject; schedule interview; record result; issue offer; accept/decline; coordinator stats and all applications |
| **Frontend** | React + Vite + Tailwind in `frontend/`: Login and Student, Company and Coordinator dashboards |
| **Demo data** | `seed.py` creates 3 students, 2 companies, 3 jobs and 6 logins (password `password123`) on first start |
| **Tests** | **None.** There is no test folder, no pytest configuration and no test dependency in `requirements.txt` |

### 1.3 Can it run on this machine right now?
Not yet. Python 3.13.5 and Node 22.18.0 are installed, and FastAPI, Pydantic, pytest, pytest-asyncio and httpx are present. **SQLAlchemy, aiosqlite, python-jose, passlib and bcrypt are missing**, so the backend cannot start. They would be installed into a virtual environment inside `Lab5/` (Iteration 0).

### 1.4 How the current workflow behaves
1. A student sees all jobs, each with an "eligible / not eligible" flag, and applies.
2. On apply, the code checks only CGPA (`cgpa < min_cgpa` rejects, so **6.5 against 6.5 passes correctly**) and active backlogs.
3. A company shortlists or rejects an applicant, schedules **one** interview, marks it PASS or FAIL, and issues an offer.
4. The student accepts or declines the offer.
5. The coordinator sees counts and a placement percentage.

### 1.5 Gap analysis against the requirements

Legend: ✅ meets the requirement · ⚠️ partly meets it · ❌ missing or contradicts it

#### A. Eligibility (the core business rule)

| Req. | Requirement | Current code | Status |
|---|---|---|---|
| FR-4.1 | `check_eligibility(student, job)` returns an `EligibilityResult(eligible, reason)` | `verify_eligibility` returns a plain `(bool, str)` tuple | ⚠️ |
| FR-4.2 | Rules R1→R4 in order, return the first failure | Only R1 and R2 exist | ❌ |
| FR-4.3 | CGPA equal to the minimum passes | `cgpa < min_cgpa` rejects, so equal passes. But CGPA is a `Float`, so values like 6.5 are compared as binary floats | ⚠️ |
| FR-4.4 | Cleared backlogs never reduce eligibility | No `cleared_backlogs` field exists | ⚠️ |
| R3 / FR-8.5 | A student who accepted an offer this season fails every other drive | **Not implemented.** A placed student can apply and accept a second offer | ❌ |
| R4 / FR-3.3 | Branch whitelist; an empty list means a pool drive | No allowed-branches data; branch is free text ("Computer Science") instead of CSE/ECE/ISE/MECH/CIVIL | ❌ |
| FR-4.5 | One eligibility function used by apply, shortlist and listing | Used by apply and listing. A shortlist run does not exist | ⚠️ |
| FR-4.6 | Students see only open, future drives they are eligible for and have not applied to | Students see every job | ❌ |
| FR-4.7 / NFR-7.1 | Plain-language reason, e.g. "CGPA 6.49 below minimum 6.5" | A reason is given, in a different wording | ⚠️ |
| NFR-9.3 | Store every eligibility decision with its reason | Not stored | ❌ |

#### B. Application status life cycle (ADR-002)

The specification allows exactly six statuses, moving forward only:
`APPLIED → SHORTLISTED → INTERVIEW_SCHEDULED → INTERVIEWED → OFFERED → ACCEPTED`

| Req. | Requirement | Current code | Status |
|---|---|---|---|
| FR-5.6 | Status changes only through transition functions | Each service function sets `application.status` directly | ❌ |
| Transition table | Only the 5 listed forward moves are allowed | **No checks at all.** For example, an `OFFERED` application can be set back to `SHORTLISTED`, and an interview can be scheduled for an application that was never shortlisted | ❌ |
| FR-7.3 | `INTERVIEWED` status | Does not exist; interview PASS/FAIL does not change the status | ❌ |
| FR-8.1/8.2 | Offer only when status is `INTERVIEWED` | An offer can be issued to **any** application, even one whose interview was FAIL or never happened | ❌ |
| FR-8.4 | Accept checks ownership, sets status, sets the accepted flag | Ownership is checked. The offer can be "responded to" again and again (accept, then decline, then accept) | ⚠️ |
| Open issue 2 | Six statuses; rejection/withdrawal only through an ADR update | Code adds `REJECTED` and `DECLINED` | ⚠️ needs a team decision (Section 6) |
| NFR-1.2 | A test for every disallowed transition | No tests | ❌ |
| NFR-9.1 | Record who changed each status and when | Not recorded | ❌ |

#### C. Applications, shortlisting, interviews and offers

| Req. | Requirement | Current code | Status |
|---|---|---|---|
| FR-5.1 | Apply only if the job exists, **is open**, the student is eligible, and not already applied | No "open" flag exists | ⚠️ |
| FR-5.2 | Domain exceptions `JobNotFound`, `NotEligible`, `AlreadyApplied` with one base class | Services raise FastAPI `HTTPException` | ❌ |
| FR-5.3 | One application per company per season | Not checked | ❌ |
| FR-5.4 | Applications scoped to the current season | No season concept | ❌ |
| NFR-8.3 | Unique (student, job) **in the database** | Checked only in code; two simultaneous requests could both succeed | ⚠️ |
| FR-6.1–6.5 | `shortlist_students(job_id)`: checks every applicant, one transaction, records reasons, safe to run twice | Does not exist; shortlisting is manual, one student at a time | ❌ |
| FR-6.6 | Email shortlisted and ineligible students; a mail failure must not undo the shortlist | Not implemented | ❌ |
| FR-7.1 | **Coordinator** schedules a round with number, time and venue | Company schedules; no round number or venue | ⚠️ |
| FR-7.2 | Several rounds, round number unique per application | `UNIQUE(application_id)` allows only one interview | ❌ |
| FR-7.4 | Student sees their own interview schedule | Shown inside "my applications" | ✅ |
| FR-8.3 / NFR-3.5 | Offer letter stored under a random, unguessable key | No offer letter at all | ❌ |
| FR-8.6 | At most one offer per application | `UNIQUE(application_id)` on offers | ✅ |

#### D. Students, companies and job listings

| Req. | Requirement | Current code | Status |
|---|---|---|---|
| FR-2.1 | USN, name, email, branch (enum), CGPA, active and cleared backlogs | No USN, no cleared backlogs, branch not an enum | ⚠️ |
| FR-2.2 | USN and email unique | Email unique; no USN | ⚠️ |
| FR-2.3 | Coordinator creates students and updates CGPA/backlogs | No endpoint | ❌ |
| FR-3.1 | Coordinator registers a company | No endpoint | ❌ |
| FR-3.2 | **Coordinator** publishes a listing with season, drive date, open flag, allowed branches | **Company** creates listings; no season, drive date, open flag or branches | ⚠️ needs a team decision (Section 6) |
| FR-3.4 | Coordinator closes a listing | Not possible | ❌ |
| FR-3.5 | Criteria editable only before the drive date | No editing at all | ❌ |

#### E. Security and access control

| Req. | Requirement | Current code | Status |
|---|---|---|---|
| FR-1.1 | JWT with three roles | Yes (`COMPANY` instead of `COMPANY_REP`) | ✅ |
| FR-1.2 | `get_current_student()`, `get_current_company()`, `get_current_coordinator()` | One generic `require_role(...)` returning the raw token payload | ⚠️ |
| FR-1.3 | A student acts only on their own data; identity from the token | Identity comes from the token (`linked_id`) | ✅ |
| FR-1.4 | A company sees only its own listings, applicants and offers | Checked for applicants and offers. **`GET /students` returns every student's CGPA, backlogs and email to every company** | ⚠️ |
| NFR-3.3 | Validate ranges (CGPA 0–10, backlogs ≥ 0, package > 0) | No range validation; a job with `min_cgpa = -5` or a negative package is accepted | ❌ |
| NFR-3.4 | Error messages reveal no internals; minimal fields | Mostly fine; see FR-1.4 above | ⚠️ |
| NFR-3.7 | Token secret kept outside the source code | `SECRET_KEY` is written in `security.py` and is now public on GitHub | ❌ |
| NFR-3.1 | Expired or invalid tokens refused | Yes (`jose` checks expiry; 12-hour lifetime) | ✅ |
| — | CORS | `allow_origins=["*"]` together with `allow_credentials=True` | ⚠️ |

#### F. Architecture, data integrity and privacy

| Req. | Requirement | Current code | Status |
|---|---|---|---|
| NFR-2.1/2.2 | Routers call only services; no business logic in routers | Several routers call repositories directly; coordinator statistics are calculated in the router; ownership checks are in routers | ❌ |
| NFR-2.4 (ADR-004) | HTTP exceptions only in routers, domain exceptions in services | Services raise `HTTPException` | ❌ |
| FR-6.4 / NFR-1.3 | Multi-record operations in one transaction | Every repository method calls `commit()` itself, so a multi-step operation cannot be made atomic | ❌ |
| NFR-8.1 | Foreign keys enforced by the database | SQLite does not enforce foreign keys unless `PRAGMA foreign_keys=ON` is set; it is not set | ❌ |
| NFR-8.2 | 3NF; one fact in one place | A student's email is stored twice (`users.email` and `students.email`) | ⚠️ |
| FR-10.1 / NFR-4.1 | Consent recorded before processing | Not implemented | ❌ |
| FR-10.2 / NFR-4.4 | Anonymise on request without breaking foreign keys | Not implemented | ❌ |
| FR-9.1 | Coordinator lists a drive's applicants with branch, CGPA, status | Yes (`/applications/job/{id}`) | ✅ |
| FR-9.2 | Counts per status per drive and per season | Only overall totals | ⚠️ |
| FR-9.3 | CSV export of a drive's shortlist | Not implemented | ❌ |
| — | Deprecated APIs | `@app.on_event("startup")` and `datetime.utcnow()` produce deprecation warnings on Python 3.13 | ⚠️ |

### 1.6 Summary of the current status
- **What works:** the basic happy path runs end to end, the layer folders exist, passwords are hashed, JWT login works, and the R1 boundary (6.5 equals 6.5) is already correct.
- **The main gaps:**
  1. Eligibility rules R3 and R4 are missing.
  2. The status life cycle is not enforced at all.
  3. There is no shortlisting run, no season concept, no privacy features, and no audit trail.
  4. Services raise HTTP errors, and repositories commit on their own.
  5. **There are zero tests**, so none of the behaviour above is protected.

---

## Part 2 – SDLC approach

We follow an **iterative SDLC**. Each iteration goes through all phases for a small slice of features, rather than designing the whole system up front. This suits a project that already runs and must keep running while it is improved.

| SDLC phase | What we do in this project | Output |
|---|---|---|
| **1. Requirements** | Use `TalentHub_Requirements_v2.docx` as the specification. Every test and change cites its FR/NFR ID. Unclear points go to Section 6 for a decision, never a silent choice | Traceability matrix (Part 5) |
| **2. Design** | Use our Lab 4 schema as the target data model. Fix the state machine, the exception classes and the layer rules before each iteration's tests are written | Design notes per iteration (Part 4) |
| **3. Implementation (TDD)** | For every behaviour: write a failing test, then the minimum code to pass it, then refactor (Part 3) | Tests and code, in that order |
| **4. Testing** | Unit, service, API and architecture tests run on every change; a manual end-to-end walkthrough of the UI at the end | Passing test suite + test report |
| **5. Deployment** | Pinned dependencies, secret from an environment variable, an updated README and run steps | Runnable project |
| **6. Maintenance/review** | Architecture drift checks as automated tests (NFR-2.7); a short review note after each iteration | Review log |

---

## Part 3 – TDD rules we will follow

These rules apply to every line of production code we write.

1. **Red:** write one test from the **specification**, never from the code's current output (NFR-1.1). Run it and **see it fail** for the expected reason. A test that passes before the code exists is checking nothing.
2. **Green:** write the **smallest** production change that makes that test pass.
3. **Refactor:** clean up the code and the test while every test stays green.
4. **One behaviour per cycle.** Never write production code without a failing test that needs it.
5. **Expected values come from the spec.** For example, the boundary table in FR-4 says "CGPA 6.50 with minimum 6.50 → eligible", so that is the expected value, whatever the code currently does.
6. **Existing behaviour we keep is pinned first.** Before changing working code, we add *characterisation tests* that record what it does now (for example, a successful login). These must pass immediately; they are a safety net, not a TDD red step, and we label them as such.
7. **Test names carry the requirement ID**, e.g. `test_FR4_3_cgpa_equal_to_minimum_is_eligible`, so the traceability matrix can be built from the test list.
8. **Every iteration ends fully green**, followed by a commit (only after the team approves committing; see Section 6).

### Test tooling (proposed)
- `pytest` and `pytest-asyncio` for unit and service tests (already installed on this machine).
- `httpx.AsyncClient` with FastAPI's ASGI transport for API tests.
- A fresh **in-memory SQLite** database per test, with `PRAGMA foreign_keys=ON`, so tests never touch `talenthub.db` and only use synthetic data (NFR-4.6).
- A new `requirements-dev.txt` for test-only packages, so the production `requirements.txt` stays clean (NFR-2.5).
- Folder layout: `backend/tests/unit/`, `backend/tests/service/`, `backend/tests/api/`, `backend/tests/architecture/`.

---

## Part 4 – Planned changes, iteration by iteration

Each iteration lists **the tests first** (written and seen failing before any code), then the code changes those tests drive.

### Iteration 0 – Test harness and safety net
- **Set-up (no production code):** create a virtual environment in `Lab5/`, install `requirements.txt` + `requirements-dev.txt`, and add `pytest.ini` and `conftest.py` (test database, test client and data factories).
- **Characterisation tests** of current behaviour we keep: login succeeds with a correct password and fails with a wrong one; a protected route without a token returns 401; a student cannot call a company-only route (403).
- **Exit:** the suite runs and these tests pass.

### Iteration 1 – Eligibility service (FR-4, R1–R4)
A pure function with no database, so it is the easiest place to start strict TDD.

**Tests written first:**

| Test | Input | Expected (from spec) |
|---|---|---|
| R1 below | CGPA 6.49, minimum 6.50 | Ineligible, "CGPA 6.49 below minimum 6.5" |
| R1 equal | CGPA 6.50, minimum 6.50 | Eligible |
| R1 above | CGPA 6.51, minimum 6.50 | Eligible |
| R2 cleared ignored | 0 active, 3 cleared, maximum 0 | Eligible |
| R2 over | 1 active, maximum 0 | Ineligible, "1 active backlogs" |
| R2 equal | 2 active, maximum 2 | Eligible |
| R3 | Already accepted an offer this season | Ineligible, "Already accepted an offer this season" |
| R4 pool | Allowed branches empty, any branch | Eligible |
| R4 whitelist in | Branch CSE, allowed {CSE, ISE} | Eligible |
| R4 whitelist out | Branch ECE, allowed {CSE} | Ineligible, "Branch ECE not in drive scope" |
| Rule order | Fails R1 and R4 together | Reason is the R1 reason (first failure) |
| All pass | Meets everything | Eligible, reason says all conditions are met |
| Not an exception | Any ineligible case | Returns a result; raises nothing (FR-4.1) |

**Code changes this drives:** an `EligibilityResult` type; `check_eligibility(student, job)` implementing R1→R4; CGPA compared as an exact decimal; a `Branch` enum. The old `verify_eligibility` callers are switched over.

### Iteration 2 – Status state machine and domain exceptions (ADR-002, FR-5.6, NFR-1.2, ADR-004)
**Tests written first:**
- The 5 allowed transitions each succeed.
- **Every other pair of statuses is rejected**, as one parametrised test covering all 6 × 6 combinations minus the 5 allowed ones (31 cases), including staying in the same status and every backward move.
- An invalid transition raises a domain exception (e.g. `InvalidTransition`), not an HTTP error.
- All domain exceptions share one base class (FR-5.2).

**Code changes:** a `transitions` module with the allowed-move table and one `transition(application, new_status, by_user)` function; a `domain/exceptions.py` module; routers translate domain exceptions into HTTP status codes.

### Iteration 3 – Data model migration toward the Lab 4 schema (NFR-8.x)
**Tests written first (database constraint tests):**
- An application cannot reference a missing student or job (foreign keys on).
- A duplicate (student, job) application is rejected **by the database**.
- Duplicate USN and duplicate email are rejected.
- CGPA outside 0–10, negative backlogs and package ≤ 0 are rejected.
- Interview round numbers are unique within an application, and round ≥ 1.
- A drive with no allowed-branch rows is treated as a pool drive.

**Code changes:** add seasons, drive date, open flag, allowed branches, USN, cleared backlogs, interview rounds and venue, offer-letter key and status history; enable `PRAGMA foreign_keys=ON`; update `seed.py`. The extent of this change depends on decision D2 in Section 6.

### Iteration 4 – Applying for a job (FR-5.1 to FR-5.5)
**Tests written first:**
- Applying to a missing job raises `JobNotFound`.
- Applying to a closed job is refused.
- An ineligible student gets `NotEligible` **carrying the eligibility reason**.
- Applying twice to the same job raises `AlreadyApplied`.
- Applying to a second drive of the **same company in the same season** is refused (FR-5.3).
- A successful application has status `APPLIED`, and a status-history row records who and when.
- The eligibility decision is stored with its reason (NFR-9.3).
- The job list for a student shows only open, future drives they are eligible for and have not applied to (FR-4.6).

**Code changes:** rewrite `apply_for_job`; move commits out of the repositories so the service controls the transaction.

### Iteration 5 – Shortlisting run (FR-6.1 to FR-6.6, NFR-1.3)
**Tests written first:**
- Eligible applicants move from `APPLIED` to `SHORTLISTED`; ineligible ones stay and get a recorded reason.
- No new applications are created by the run.
- Running it twice gives the same final state (idempotent).
- If an error happens part-way through, **no** changes are kept (atomic).
- A failing email sender does not undo the shortlist (FR-6.6, NFR-6.3), tested with a fake sender.

**Code changes:** a new `shortlist_students(job_id)` service function, a coordinator endpoint, and a notification interface (the email library depends on decision D5).

### Iteration 6 – Interviews and offers (FR-7, FR-8)
**Tests written first:**
- An interview can be scheduled only for a `SHORTLISTED` application; the status becomes `INTERVIEW_SCHEDULED`.
- Several rounds are allowed; a duplicate round number is refused.
- Recording that the interview stage is complete sets `INTERVIEWED`.
- An offer can be issued only to an `INTERVIEWED` application; every other status is refused.
- The offer-letter key is random and differs between two offers for the same student and company.
- Only the owning student can accept; accepting sets `ACCEPTED` and the accepted flag in **one** transaction (NFR-8.4).
- **After accepting, the same student fails R3 for every other drive in the season** (FR-8.5).
- An offer cannot be accepted twice.

### Iteration 7 – Access control and security (FR-1, NFR-3)
**Tests written first (API level):**
- Each protected route returns 401 with a missing, invalid or expired token.
- Student A cannot read or act on student B's applications or offers (IDOR; NFR-3.2).
- Company X cannot see company Y's applicants or issue offers on Y's drives.
- A company cannot list all students' CGPAs and emails (NFR-3.4).
- Invalid inputs (CGPA 11, negative backlogs, package 0) are rejected with 422.
- The app refuses to start without a secret key from the environment (NFR-3.7).

**Code changes:** `get_current_student()`, `get_current_company()`, `get_current_coordinator()` dependencies; Pydantic range validation; secret moved to an environment variable; CORS narrowed to the frontend address.

### Iteration 8 – Coordinator features and reporting (FR-2.3, FR-3.1, FR-3.4, FR-3.5, FR-9)
**Tests written first:** the coordinator can create students and companies, publish and close drives, and edit criteria only before the drive date; per-status counts are correct for a drive and for the season; the CSV export of a shortlist has the right header and rows.

### Iteration 9 – Privacy (FR-10, NFR-4)
**Tests written first:** a student without placement consent is not processed (cannot be shortlisted); consent can be withdrawn; anonymising a student blanks personal fields while their applications and offers stay valid.

### Iteration 10 – Architecture drift checks (NFR-2.1 to NFR-2.7)
**Tests written first (they scan the source code):**
- No router file imports a repository or runs a query.
- No service file imports `fastapi` or raises `HTTPException`.
- No service module imports another service module.
- No query is built by joining strings (NFR-3.6).

Some of these will fail against the current code. That is expected: they drive the refactoring of routers and services, which earlier iterations will already have partly done.

### Iteration 11 – Frontend and end-to-end check
Update the React pages for the new fields (USN, branch, rounds, venue, reasons) and the coordinator-run shortlisting. Then run the README walkthrough by hand and record the result. Automated frontend tests are optional; see decision D4.

---

## Part 5 – Traceability (filled in as the iterations finish)

| Requirement | Test(s) | Iteration | Status (6 Nov 2026) |
|---|---|---|---|
| Existing auth behaviour | `tests/api/test_characterisation_auth.py` | 0 | ✅ 4 pass |
| FR-4.1 – FR-4.7 | `tests/unit/test_eligibility.py` | 1 | ✅ 20 pass |
| ADR-002 + ADR-005, FR-5.6, NFR-1.2 | `tests/unit/test_transitions.py` | 2 | ✅ 68 pass (10 allowed, 54 disallowed, 4 checks) |
| NFR-8.1 – NFR-8.3, NFR-3.3 | `tests/service/test_constraints.py` | 3 | ✅ pass |
| FR-5.1 – FR-5.5, FR-4.6, NFR-9.1, NFR-9.3 | `tests/service/test_apply.py` | 4 | ✅ pass |
| FR-6.1 – FR-6.6, NFR-1.3, NFR-6.3 | `tests/service/test_shortlist.py` | 5 | ✅ pass |
| FR-7.x, FR-8.x, NFR-8.4 | `tests/service/test_interviews_offers.py` | 6 | ✅ pass |
| FR-1.x, NFR-3.x, full workflow | `tests/api/test_api.py` | 7 | ✅ 8 pass |
| FR-2.3, FR-3.x, FR-9.x, FR-10.x, NFR-4.x | `tests/service/test_admin_privacy.py` | 8–9 | ✅ pass |
| NFR-2.1 – NFR-2.7, NFR-3.6, FR-1.2 | `tests/architecture/test_layers.py` | 10 | ✅ 59 pass |
| Frontend | `npx vite build` + backend smoke run | 11 | ✅ builds; manual UI walkthrough **not yet done** |

**Total: 219 tests, all passing** (unit 88, service 60, API 12, architecture 59).

### Results notes (what changed from the plan)
- Iterations 3–6 and 8–9 were done as one batch: all their tests were written and run red first, then the code was written. File names differ slightly from the planned ones (as in the table above).
- The Lab 4 SQL views are implemented as repository queries (e.g. `has_accepted_offer_in_season`), because SQLAlchemy `create_all` does not create views.
- `job_listings` keeps `role_title`, `description` and `package_lpa` (not in the Lab 4 schema) so the existing UI keeps working; `companies` keeps `description`.
- `placement_service` imports `eligibility_service`: an allowed exception to NFR-2.3, because FR-4.5 requires every use case to call the single rule function. The architecture test documents this exception.
- The offer-letter key is generated by the server (random 64 hex characters) rather than supplied by the caller.
- The token secret comes from `TALENTHUB_SECRET_KEY`; without it a random development key is used, and production mode refuses to start.
- Decisions D3–D5 used my recommendations, because they were not answered.
- Not done: the coordinator dashboard has no "Run shortlisting" button yet (the API `POST /jobs/{id}/shortlist` exists); email is log-only (D5); the manual walkthrough in the browser has not been done.

**Not planned to be tested automatically:** performance targets (NFR-5), availability and backups (NFR-6), and WCAG accessibility (NFR-7.3). These are marked "proposed target" in the specification and need real infrastructure; they will be listed as open in the final report.

---

## Part 6 – Decisions the team must make before coding

None of these will be decided silently. My recommendation is given for each.

| No. | Decision | Options | Recommendation |
|---|---|---|---|
| **D1** | Statuses `REJECTED` and `DECLINED` exist in the code but not in the six-status spec (open issue 2) | (a) Remove them and follow the spec exactly; (b) keep them as end states and write an ADR update | **(b)**: a company does need to reject, and a student does need to decline. Record it in an ADR so it's a documented decision, not drift |
| **D2** | How far to change the database | (a) Move to our full Lab 4 12-table schema; (b) add only the columns and tables the FRs need to the current 7 tables | **(a)**, done step by step in Iteration 3. It's our own reviewed design and covers seasons, history and consent |
| **D3** | Who publishes drives and schedules interviews | (a) Coordinator, as the spec says (FR-3.2, FR-7.1); (b) keep the company doing it; (c) both | **(c)**: coordinator per the spec, and the company keeps it for its own drives, matching open issue 5 |
| **D4** | Frontend scope | (a) Backend TDD only, minimal UI updates; (b) also add automated frontend tests | **(a)**: the requirements are backend rules; UI checked by a manual walkthrough |
| **D5** | Email notifications (FR-6.6) | (a) An interface with a fake sender in tests and a log-only sender in development; (b) real SMTP | **(a)**: no new library and no real emails during development |
| **D6** | Git workflow | Where we commit, and whether to push to the team's GitHub repo | Work on a new branch (e.g. `lab5-tdd`), commit after each green iteration, and **push only when you say so** |
| **D7** | Installing packages | A virtual environment inside `Lab5/` (stays in the sandbox) | Approve the venv in `Lab5/talenthub-placement-portal/backend/venv`. The repo's `.gitignore` already excludes `backend/venv/`, so it will never be committed |

---

## Part 7 – Definition of done (whole project)
- Every FR in sections 3.1–3.10 of the specification has at least one passing test, or is listed as an open item with a reason.
- All 31 disallowed status transitions have rejecting tests.
- The architecture drift tests pass.
- The app starts from the README steps on a clean machine, and the manual walkthrough succeeds.
- No secret is in the source code, and only synthetic data is used.
