# Phase 2: Creation Council - Kanban Tasks

**Sprint Dates:** Dec 1 - Dec 5  
**Goal:** Implement `spec_designer`, the Creation Pipeline, and the Correction Loop.

---

## 📋 To Do (Ready for Dev)

### 2. Pipeline & Workflow
- [ ] **[Task 2.7]** Define the `specialist_creation` pipeline config.

### 3. Integration
- [ ] **[Task 2.8]** Connect `Orchestrator` to trigger creation when no match found.
- [ ] **[Task 2.9]** End-to-End Test: "Create a safe echo agent" (Should pass).
- [ ] **[Task 2.10]** End-to-End Test: "Create a dangerous file deleter" (Should fail/correct).

---

## 🚧 In Progress

*(None)*

---

## ✅ Done

- [x] **[Doc 1]** Create `docs/phase2/spec_designer_specs.md`
- [x] **[Doc 2]** Create `docs/phase2/creation_workflow.md`
- [x] **[Doc 3]** Create `docs/phase2/kanban_tasks.md`
- [x] **[Task 2.1]** Create `agents/spec_designer.py`
- [x] **[Task 2.2]** Implement `INTERVIEW` vs `GENERATE` logic
- [x] **[Task 2.3]** Inject `dangerous_patterns` context
- [x] **[Task 2.4]** Unit test SpecDesignerAgent
- [x] **[Task 2.5]** Update `PipelineExecutor` (or create new `CreationPipeline`) to handle loops/retries.
- [x] **[Task 2.6]** Implement the "Correction Loop" logic (Catch Minister error -> Feed back to Designer).

---

## 📅 Daily Schedule

### Day 1 (Dec 1): Spec Designer Implementation
- **Goal:** A working `spec_designer` that produces valid specs.
- **Tasks:** 2.1, 2.2, 2.3, 2.4.

### Day 2 (Dec 2): Pipeline & Loop
- **Goal:** The system can retry and self-correct.
- **Tasks:** 2.5, 2.6, 2.7.

### Day 3 (Dec 3): Integration & Testing
- **Goal:** Full flow from User Request to Unverified Agent.
- **Tasks:** 2.8, 2.9, 2.10.

---

## 🚩 Blockers / Risks

- **Risk:** LLM might struggle to fix JSON errors precisely. *Mitigation: Use strict output parsers or specific error prompting.*
- **Risk:** Infinite loops in correction. *Mitigation: Hard limit of 3 retries.*
