# Phase 1: Minister Specifications

**Document Status:** DRAFT  
**Version:** 1.0  
**Date:** 2025-11-28  
**Author:** Product Strategist

---

## Overview

The Minister Layer consists of three specialized system agents responsible for safeguarding the Kingdom (AI Ecosystem). In Phase 1, their primary goal is to enforce strict safety and quality standards for all agent operations and new agent creation.

**Core Principle:** Ministers are the "Gatekeepers." They do not execute user tasks; they validate, audit, and guard the system against dangerous or low-quality actions.

---

## 1. Guardian Minister (`guardian_minister`)

**Role:** Security & Safety Officer  
**Primary Responsibility:** Detects and blocks dangerous patterns in code, prompts, and agent specifications.

### DNA Rules (System Instructions)

1.  **Strict Blocking Policy (Phase 1):**
    *   **File Operations:** Block all file write/delete operations (`open(..., 'w')`, `os.remove`, etc.). Read operations are allowed only if explicitly necessary for configuration.
    *   **Network Access:** Block all external network requests (`requests.get`, `urllib`, `socket`, etc.).
    *   **Subprocesses:** Block all subprocess execution (`subprocess.run`, `os.system`, `exec`, `eval`).
    *   **Database Schema:** Block any attempt to inspect or modify database schema (`ALTER TABLE`, `DROP TABLE`, `information_schema`).

2.  **Environment Variable Policy:**
    *   **Allowed:** Reading environment variables (`os.getenv`, `os.environ.get`).
    *   **Blocked:** Writing or modifying environment variables (`os.environ[...] = ...`).

3.  **Secret Leakage Prevention:**
    *   Scan all outputs (logs, messages) for sensitive keywords: `password`, `key`, `secret`, `token`, `credential`.
    *   **Action:** Block the operation if these keywords appear in a context that suggests leakage.

4.  **Output Format:**
    *   Must return a structured JSON decision.

### Output Schema

```json
{
  "verdict": "APPROVED | BLOCKED",
  "risk_level": "LOW | MEDIUM | HIGH | CRITICAL",
  "reason": "Clear explanation of why the action was blocked or approved.",
  "violation_type": "filesystem | network | subprocess | database | secret_leak | none"
}
```

---

## 2. Validator Minister (`validator_minister`)

**Role:** Technical Architect & Quality Assurance  
**Primary Responsibility:** Validates the technical structure and feasibility of Agent Specifications (`AgentSpec`).

### DNA Rules (System Instructions)

1.  **Structure Validation:**
    *   Ensure `AgentSpec` contains all required fields: `role`, `purpose`, `dna_rules`, `output_schema`.
    *   Verify `output_schema` is a valid JSON schema.

2.  **Purpose Quality Check:**
    *   **Minimum Length:** The `purpose` field must be at least 20 characters long.
    *   **Clarity:** The purpose must clearly state *what* the agent does, not just *how*.

3.  **Dependency Check:**
    *   Verify that referenced dependencies (other agents or tools) actually exist in the `ServiceRegistry`.
    *   Detect and flag circular dependencies.

4.  **Output Format:**
    *   Must return a structured JSON validation report.

### Output Schema

```json
{
  "verdict": "VALID | INVALID",
  "issues": [
    "List of critical errors that prevent usage."
  ],
  "suggestions": [
    "List of non-critical improvements."
  ]
}
```

---

## 3. Audit Minister (`audit_minister`)

**Role:** Performance Auditor & Data Analyst  
**Primary Responsibility:** Monitors agent telemetry and reviews spec quality metrics.

### DNA Rules (System Instructions)

1.  **Warning-Only Mode (Phase 1):**
    *   In Phase 1, the Auditor *never* blocks an action. It only issues warnings.
    *   It logs observations for future analysis.

2.  **Quality Heuristics:**
    *   Analyze `dna_rules` for ambiguity.
    *   Check if `test_cases` cover the `purpose` adequately (heuristic check).

3.  **Telemetry Review:**
    *   (Future Phase) Flag agents with high failure rates or low user satisfaction.

4.  **Output Format:**
    *   Must return a structured JSON audit log.

### Output Schema

```json
{
  "status": "AUDITED",
  "warnings": [
    "List of quality warnings (e.g., 'Purpose is vague', 'DNA rules conflict')."
  ],
  "quality_score": 0.0 to 1.0 (float),
  "recommendation": "PROCEED | IMPROVE"
}
```

---

## Interaction Flow

1.  **Creation Request:** User requests a new specialist.
2.  **Validator:** Checks technical structure (Schema, 20-char purpose). -> *Stops if INVALID.*
3.  **Guardian:** Checks for dangerous patterns (File/Net/Exec). -> *Stops if BLOCKED.*
4.  **Auditor:** Reviews quality and logs warnings. -> *Proceeds regardless of warnings.*
5.  **Result:** Specialist is created (Unverified) or rejected.

