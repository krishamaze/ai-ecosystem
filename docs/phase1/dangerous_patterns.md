# Phase 1: Dangerous Patterns Blocklist

**Document Status:** FINAL  
**Enforced By:** `guardian_minister`  
**Phase:** 1 (Strict Mode)

---

## 1. File System Operations
**Policy:** Block all write/delete operations. Read is allowed for configuration only.

| Pattern (Regex/Code) | Action | Reason |
| :--- | :--- | :--- |
| `open\(.*['"]w['"].*\)` | **BLOCK** | File write detected. |
| `open\(.*['"]a['"].*\)` | **BLOCK** | File append detected. |
| `open\(.*['"]x['"].*\)` | **BLOCK** | File create detected. |
| `os\.remove` | **BLOCK** | File deletion detected. |
| `os\.rmdir` | **BLOCK** | Directory deletion detected. |
| `shutil\.rmtree` | **BLOCK** | Recursive directory deletion detected. |
| `pathlib\.Path\(.*\)\.write_text` | **BLOCK** | Pathlib write detected. |

---

## 2. Network Operations
**Policy:** Block all external network access.

| Pattern (Regex/Code) | Action | Reason |
| :--- | :--- | :--- |
| `import requests` | **BLOCK** | Network library import. |
| `import urllib` | **BLOCK** | Network library import. |
| `import socket` | **BLOCK** | Low-level network access. |
| `import aiohttp` | **BLOCK** | Async network library. |
| `requests\.get` | **BLOCK** | HTTP GET request. |
| `requests\.post` | **BLOCK** | HTTP POST request. |

---

## 3. Subprocess & System Execution
**Policy:** Block all shell command execution.

| Pattern (Regex/Code) | Action | Reason |
| :--- | :--- | :--- |
| `import subprocess` | **BLOCK** | Subprocess library. |
| `os\.system` | **BLOCK** | Shell execution. |
| `os\.popen` | **BLOCK** | Shell execution. |
| `subprocess\.run` | **BLOCK** | Shell execution. |
| `exec\(.*\)` | **BLOCK** | Dynamic code execution (high risk). |
| `eval\(.*\)` | **BLOCK** | Dynamic code evaluation (high risk). |

---

## 4. Database Schema Modifications
**Policy:** Block all schema changes. Only DML (Data Manipulation Language) allowed on specific tables (future).

| Pattern (Regex/Code) | Action | Reason |
| :--- | :--- | :--- |
| `DROP TABLE` | **BLOCK** | Destructive schema change. |
| `ALTER TABLE` | **BLOCK** | Schema modification. |
| `TRUNCATE TABLE` | **BLOCK** | Mass data deletion. |
| `CREATE TABLE` | **BLOCK** | Unauthorized schema creation. |
| `information_schema` | **BLOCK** | Schema inspection probing. |

---

## 5. Secret Leakage
**Policy:** Block output containing potential secrets.

| Keyword | Action | Context |
| :--- | :--- | :--- |
| `password` | **BLOCK** | Logs or user messages. |
| `secret` | **BLOCK** | Logs or user messages. |
| `api_key` | **BLOCK** | Logs or user messages. |
| `token` | **BLOCK** | Logs or user messages. |
| `credential` | **BLOCK** | Logs or user messages. |

---

## 6. Environment Variables
**Policy:** Read-only access allowed.

| Pattern | Action | Reason |
| :--- | :--- | :--- |
| `os\.environ\[.*\]\s*=` | **BLOCK** | Environment variable modification. |
| `os\.putenv` | **BLOCK** | Environment variable modification. |

---

## Escalation Protocol
If a legitimate use case requires one of these patterns:
1.  Do NOT bypass the block.
2.  Document the requirement in `docs/phase1/phase1_completion_report.md`.
3.  Request Founder approval for an exception in Phase 2.

