# PHASE 1 - MINISTERS LAYER: PRODUCT STRATEGIST ASSIGNMENT

**Document Status:** DRAFT - Ready To Start  
**Assigned To:** Product Strategist  
**Created:** 2025-11-28  
**Review By:** Founder (Root)  
**Deadline:** 2025-12-02 (5 days)

---

## APPROVAL CONFIRMATION

**Decisions Confirmed by Founder:**
- ✅ Block everything in Phase 1 (all file/system ops, network, subprocess)
- ✅ Allow read env vars (for config), block write env vars
- ✅ Allow console logging, but block if it contains "password", "key", or "secret"
- ✅ 20-character minimum purpose length is required
- ✅ audit_minister issues warnings only (does not block creation)
- ✅ Add "access database schema" to block list (no schema inspection in Phase 1)
- ✅ System agents (ministers) do NOT require admin approval
- ✅ Relax restrictions only in later phases and only with telemetry justification

**Sign-off:**  
- [x] Founder approved  
- Date approved: 2025-11-28  
- Signature/Initials: Founder

---

## MISSION FOR PRODUCT STRATEGIST

Convert KINGDOM.md architecture → executable, reviewable specs for Full Stack Developer.

**Your Output (5 Documents in docs/phase1/):**
1. `minister_specs.md` - DNA rules for 3 ministers (plain English)
2. `test_scenarios.md` - Test cases for each minister
3. `kanban_tasks.md` - Daily task breakdown (5 days)
4. `dangerous_patterns.md` - Final dangerous patterns list (merge in founder feedback above)
5. `phase1_completion_report.md` - End-of-phase summary

---

### WHAT TO DO

**Today (Nov 28):**
- Create docs/phase1/ folder if not exists.
- Complete minister_specs.md (2-3 hours)
- Complete test_scenarios.md (1-2 hours)

**Nov 29 (Tomorrow):**
- Complete dangerous_patterns.md (merge founder feedback above, ~1 hour)
- Complete kanban_tasks.md (1 hour)
- Submit all 4 docs to Founder for review

**After Approval:**
- Handoff specs to Full Stack Developer
- Monitor task progress and unblock as needed

**End of Phase (Dec 2):**
- Complete phase1_completion_report.md
- Request sign-off from Founder before moving to Phase 2

---

## ESCALATION PROTOCOL (Document Everything)

- If business logic is unclear, escalate in writing using docs/phase1/kanban_tasks.md.
- If you identify security or architecture risks, document them in dangerous_patterns.md and notify Founder immediately.
- All deviations from specs or new recommendations should be collected in phase1_completion_report.md.

---

## SUCCESS CRITERIA

- All 4 preparation docs delivered and approved by Founder (NOV 30).
- Development completed by Full Stack Dev (DEC 2).
- All minister test cases passing (≥80% coverage).
- phase1_completion_report.md submitted and approved.
- Phase 2 only starts after explicit founder sign-off.

---

**By direction of Founder.**
