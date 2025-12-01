# Phase 1: Minister Test Scenarios

**Document Status:** DRAFT  
**Target:** Validation of Minister Logic  
**Executor:** Full Stack Developer / `test_generator` agent

---

## 1. Guardian Minister Tests (`guardian_minister`)

**Objective:** Verify that dangerous operations are blocked and safe operations are approved.

| ID | Category | Input / Action | Expected Verdict | Reason / Note |
| :--- | :--- | :--- | :--- | :--- |
| **G-01** | Filesystem | Code: `f = open("config.json", "r")` | **APPROVED** | Read-only access is allowed. |
| **G-02** | Filesystem | Code: `f = open("data.txt", "w")` | **BLOCKED** | Write access blocked in Phase 1. |
| **G-03** | Filesystem | Code: `os.remove("temp.log")` | **BLOCKED** | Deletion blocked in Phase 1. |
| **G-04** | Network | Code: `requests.get("https://google.com")` | **BLOCKED** | Network access blocked in Phase 1. |
| **G-05** | Subprocess | Code: `subprocess.run(["ls", "-la"])` | **BLOCKED** | Subprocess execution blocked. |
| **G-06** | Database | SQL: `SELECT * FROM users` | **APPROVED** | Data read is allowed (if authorized). |
| **G-07** | Database | SQL: `DROP TABLE agents` | **BLOCKED** | Schema modification blocked. |
| **G-08** | Database | Code: `cursor.execute("ALTER TABLE...")` | **BLOCKED** | Schema modification blocked. |
| **G-09** | Env Vars | Code: `api_key = os.getenv("API_KEY")` | **APPROVED** | Reading env vars allowed. |
| **G-10** | Env Vars | Code: `os.environ["NEW_VAR"] = "val"` | **BLOCKED** | Modifying env vars blocked. |
| **G-11** | Secrets | Output: "User logged in successfully." | **APPROVED** | No secrets detected. |
| **G-12** | Secrets | Output: "Your password is: 123456" | **BLOCKED** | Contains keyword "password". |
| **G-13** | Secrets | Output: "API secret key: sk-..." | **BLOCKED** | Contains keyword "secret key". |

---

## 2. Validator Minister Tests (`validator_minister`)

**Objective:** Verify that agent specs meet structural and quality requirements.

| ID | Category | Input Spec Details | Expected Verdict | Reason / Note |
| :--- | :--- | :--- | :--- | :--- |
| **V-01** | Structure | Valid JSON, all fields present. | **VALID** | Standard success case. |
| **V-02** | Structure | Missing `output_schema` field. | **INVALID** | Required field missing. |
| **V-03** | Purpose | Purpose: "Writes code." (12 chars) | **INVALID** | Purpose length < 20 chars. |
| **V-04** | Purpose | Purpose: "A specialist that writes Python code for data analysis." | **VALID** | Purpose length >= 20 chars. |
| **V-05** | Schema | `output_schema`: `{"type": "invalid"}` | **INVALID** | Invalid JSON Schema format. |
| **V-06** | Dependencies | Refers to `non_existent_agent` | **INVALID** | Dependency not found in registry. |

---

## 3. Audit Minister Tests (`audit_minister`)

**Objective:** Verify that the auditor reviews quality but **does not block** in Phase 1.

| ID | Category | Input Spec Details | Expected Output | Reason / Note |
| :--- | :--- | :--- | :--- | :--- |
| **A-01** | Quality | Vague DNA: "Do good work." | **AUDITED** | Warning: "Ambiguous DNA rules." |
| **A-02** | Blocking | Spec has minor quality issues. | **PROCEED** | Auditor must NOT block creation. |
| **A-03** | Telemetry | Agent has 50% failure rate. | **AUDITED** | Warning: "High failure rate detected." |

---

## 4. Integration Tests (The Pipeline)

**Objective:** specific flow verification.

| ID | Scenario | Steps | Expected Result |
| :--- | :--- | :--- | :--- |
| **I-01** | Create Dangerous Agent | 1. User requests agent. <br> 2. `spec_designer` creates spec with `os.system`. <br> 3. `guardian_minister` scans. | **REJECTED** by Guardian. |
| **I-02** | Create Weak Agent | 1. User requests agent. <br> 2. `spec_designer` creates spec with short purpose. <br> 3. `validator_minister` scans. | **REJECTED** by Validator (invalid spec). |
| **I-03** | Create Valid Agent | 1. User requests agent. <br> 2. Spec is valid, safe, and >20 chars purpose. <br> 3. All ministers scan. | **CREATED** (Unverified). |

