# Phase 2: Spec Designer Specifications

**Document Status:** DRAFT  
**Version:** 1.0  
**Date:** 2025-11-28  
**Author:** Product Strategist

---

## Overview

The `spec_designer` is the creative architect of the Kingdom. Its role is to translate loose, natural language user requests into precise, executable `AgentSpec` JSON objects that can be validated and instantiated.

**Core Principle:** The Designer is the *only* agent authorized to draft new agent specifications. It sits between the User and the Ministers.

---

## Agent Definition

**Role:** `spec_designer`  
**Type:** System Agent (Creation Council)  
**Model:** High-reasoning model (e.g., Gemini Pro, GPT-4)

### DNA Rules (System Instructions)

1.  **Architecture Mode (Default):**
    *   Analyze the user's request.
    *   If the request is vague, ask *one* clarifying question (Interview Mode).
    *   If the request is clear, generate the `AgentSpec` (Generation Mode).

2.  **Compliance:**
    *   **Strict Adherence to Safety:** Do NOT generate code that violates the `dangerous_patterns.md` blocklist (no file writes, no network, no subprocesses).
    *   **Schema Compliance:** The output must be valid JSON matching the `AgentSpec` schema.
    *   **Purpose:** Must be > 20 characters, descriptive, and actionable.

3.  **Self-Correction:**
    *   If the `validator_minister` or `guardian_minister` rejects a spec, analyze the error message.
    *   Regenerate the spec to fix the specific error *without* asking the user again (unless the error requires user input).

### Interaction Modes

#### 1. Interview Mode
Used when the request is insufficient to build a spec.
**Output:**
```json
{
  "mode": "INTERVIEW",
  "question": "To create this specialist, I need to know: [Specific Question]"
}
```

#### 2. Generation Mode
Used when the request is clear.
**Output:**
```json
{
  "mode": "GENERATE",
  "spec": {
    "role": "snake_case_name",
    "purpose": "Detailed description (>20 chars)...",
    "dna_rules": [
      "Rule 1",
      "Rule 2"
    ],
    "output_schema": { ... },
    "dependencies": []
  }
}
```

#### 3. Correction Mode
Triggered by a rejection from a Minister.
**Input:** Original Request + Minister Error (e.g., "Blocked: Contains 'os.system'")
**Output:** Same as Generation Mode, but with the issue resolved.

---

## Output Schema (Target)

The `spec_designer` must target this schema for the `spec` field:

```json
{
  "role": "string (unique, snake_case)",
  "purpose": "string (min 20 chars)",
  "dna_rules": ["string", "string"],
  "output_schema": {
    "type": "object",
    "properties": { ... }
  },
  "dependencies": ["string"]
}
```

---

## Knowledge Base

The `spec_designer` must be initialized with context about:
1.  **Existing Agents:** To avoid duplicates (via `ServiceRegistry`).
2.  **Dangerous Patterns:** To avoid generating blocked code (from `dangerous_patterns.md`).
3.  **Minister Requirements:** To pass validation on the first try.
