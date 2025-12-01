# Phase 1: Minister Layer - Kanban Tasks

**Sprint Dates:** Nov 28 - Dec 2  
**Goal:** Implement Guardian, Validator, and Auditor Ministers with tests.

---

## 📋 To Do (Ready for Dev)

*(None - Phase 1 Complete)*

---

## 🚧 In Progress

*(None)*

---

## ✅ Done

- [x] **[Doc 1]** Create `minister_specs.md` (Product Strategist)
- [x] **[Doc 2]** Create `test_scenarios.md` (Product Strategist)
- [x] **[Doc 3]** Create `dangerous_patterns.md` (Product Strategist)
- [x] **[Doc 4]** Create `kanban_tasks.md` (Product Strategist)
- [x] **[Task 1.1]** Rename `agent_auditor` to `audit_minister` in `agent_specs.json` and code.
- [x] **[Task 1.2]** Update `AGENT_DEPENDENCIES` to reflect the new minister names.
- [x] **[Task 1.3]** Implement `guardian_minister` (extends `RequestGuard`) with Phase 1 blocklist.
- [x] **[Task 1.4]** Implement `validator_minister` (checks structure, purpose length, valid JSON schema).
- [x] **[Task 1.5]** Implement `audit_minister` (warning only mode).
- [x] **[Task 2.1]** Create `tests/test_ministers.py` with `guardian_minister` test cases.
- [x] **[Task 2.2]** Add `validator_minister` test cases.
- [x] **[Task 2.3]** Add `audit_minister` test cases.
- [x] **[Task 3.1]** Verify telemetry recording for all minister actions.
- [x] **[Task 4.1]** Run full integration test (mock creation pipeline).
- [x] **[Task 5.1]** Prepare `phase1_completion_report.md`.

---

## 📅 Daily Schedule

### Day 1 (Nov 28): Specs & Setup
- **Goal:** Specs approved, repo ready.
- **Tasks:**
    - [x] Submit 4 specs docs.
    - [x] Rename `agent_auditor` (Task 1.1).

### Day 2 (Nov 29): Guardian & Validator
- **Goal:** Security and Structure checks working.
- **Tasks:**
    - [x] Implement `guardian_minister`.
    - [x] Implement `validator_minister`.
    - [x] Update dependencies.

### Day 3 (Nov 30): Auditor & Tests
- **Goal:** Telemetry and first test pass.
- **Tasks:**
    - [x] Implement `audit_minister` (Task 1.5).
    - [x] Write unit tests (Tasks 2.1 - 2.3).

### Day 4 (Dec 1): Integration & Refinement
- **Goal:** All tests passing.
- **Tasks:**
    - [x] Run integration tests (Task 4.1).
    - [x] Fix bugs.
    - [x] Verify telemetry.

### Day 5 (Dec 2): Final Review & Sign-off
- **Goal:** Phase 1 Complete.
- **Tasks:**
    - [x] Submit completion report.
    - [ ] Founder review.

---

## 🚩 Blockers / Escalations

- **Resolved:** Telemetry schema mismatch (missing memory/rag columns) and constraint violation on `human_feedback`. Fixed by modifying `PipelineExecutor` to handle current schema.
- **Resolved:** `AgentRunner` needed modification to support Python-based ministers.
