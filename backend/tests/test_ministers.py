import pytest
import sys
import os

# Add parent directory to path so we can import orchestrator if running from backend/tests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.agents.guardian_minister import GuardianMinister
from orchestrator.agents.validator_minister import ValidatorMinister
from orchestrator.agents.audit_minister import AuditMinister

# --- Guardian Tests ---

def test_G01_filesystem_read():
    """G-01: Filesystem Read - APPROVED"""
    code = 'f = open("config.json", "r")'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "APPROVED"

def test_G02_filesystem_write():
    """G-02: Filesystem Write - BLOCKED"""
    code = 'f = open("data.txt", "w")'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "FILESYSTEM"

def test_G03_filesystem_remove():
    """G-03: Filesystem Delete - BLOCKED"""
    code = 'os.remove("temp.log")'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"

def test_G04_network_request():
    """G-04: Network Request - BLOCKED"""
    code = 'requests.get("https://google.com")'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "NETWORK"

def test_G05_subprocess():
    """G-05: Subprocess - BLOCKED"""
    code = 'subprocess.run(["ls", "-la"])'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "SUBPROCESS"

def test_G06_database_select():
    """G-06: Database Select - APPROVED"""
    code = 'SELECT * FROM users'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "APPROVED"

def test_G07_database_drop():
    """G-07: Database Drop - BLOCKED"""
    code = 'DROP TABLE agents'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "DATABASE"

def test_G08_database_alter():
    """G-08: Database Alter - BLOCKED"""
    code = 'cursor.execute("ALTER TABLE...")'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"

def test_G09_env_vars_read():
    """G-09: Env Vars Read - APPROVED"""
    code = 'api_key = os.getenv("API_KEY")'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "APPROVED"

def test_G10_env_vars_write():
    """G-10: Env Vars Write - BLOCKED"""
    code = 'os.environ["NEW_VAR"] = "val"'
    guardian = GuardianMinister(code)
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "ENV_VARS"

def test_G11_secrets_safe():
    """G-11: Secrets Safe - APPROVED"""
    output = "User logged in successfully."
    guardian = GuardianMinister(output, context="output")
    decision = guardian.get_decision()
    assert decision["verdict"] == "APPROVED"

def test_G12_secrets_password():
    """G-12: Secrets Password - BLOCKED"""
    output = "Your password is: 123456"
    guardian = GuardianMinister(output, context="output")
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "secret_leak"

def test_G13_secrets_key():
    """G-13: Secrets Key - BLOCKED"""
    output = "API secret key: sk-..."
    guardian = GuardianMinister(output, context="output")
    decision = guardian.get_decision()
    assert decision["verdict"] == "BLOCKED"


# --- Validator Tests ---

def test_V01_structure_valid():
    """V-01: Valid Spec - VALID"""
    spec = {
        "role": "test_agent",
        "purpose": "A specialist that writes Python code for data analysis.",
        "dna_rules": ["rule1"],
        "output_schema": {"type": "object"}
    }
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    assert result["verdict"] == "VALID"

def test_V02_structure_missing_field():
    """V-02: Missing Field - INVALID"""
    spec = {
        "role": "test_agent",
        "purpose": "Valid purpose but missing schema."
    }
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    assert result["verdict"] == "INVALID"
    assert "Missing required field: output_schema" in result["issues"]

def test_V03_purpose_short():
    """V-03: Short Purpose - INVALID"""
    spec = {
        "role": "test_agent",
        "purpose": "Writes code.",
        "dna_rules": [],
        "output_schema": {}
    }
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    assert result["verdict"] == "INVALID"
    assert "Purpose must be at least 20 characters long." in result["issues"]

def test_V04_purpose_long():
    """V-04: Long Purpose - VALID"""
    spec = {
        "role": "test_agent",
        "purpose": "A specialist that writes Python code for data analysis.",
        "dna_rules": [],
        "output_schema": {}
    }
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    assert result["verdict"] == "VALID"

def test_V05_schema_invalid():
    """V-05: Invalid Schema - INVALID"""
    spec = {
        "role": "test_agent",
        "purpose": "A specialist that writes Python code for data analysis.",
        "dna_rules": [],
        "output_schema": {"type": "invalid"}
    }
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    assert "Invalid JSON Schema type: invalid" in result["issues"]
    assert result["verdict"] == "INVALID"

def test_V06_dependencies_invalid():
    """V-06: Invalid Dependency - INVALID"""
    spec = {
        "role": "test_agent",
        "purpose": "A specialist that writes Python code for data analysis.",
        "dna_rules": [],
        "output_schema": {},
        "dependencies": ["non_existent_agent"]
    }
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    assert result["verdict"] == "INVALID"
    assert "Dependency not found in registry: non_existent_agent" in result["issues"]


# --- Auditor Tests ---

def test_A01_quality_ambiguous():
    """A-01: Ambiguous DNA - AUDITED (Warning)"""
    spec = {
        "dna_rules": ["Do good work."]
    }
    auditor = AuditMinister()
    result = auditor.audit_spec(spec)
    assert result["status"] == "AUDITED"
    assert any("Ambiguous DNA rule" in w for w in result["warnings"])

def test_A02_blocking_policy():
    """A-02: Blocking Policy - PROCEED"""
    spec = {
        "dna_rules": ["Do good work."] # Has issue
    }
    auditor = AuditMinister()
    result = auditor.audit_spec(spec)
    assert result["recommendation"] == "PROCEED" # Should not block

def test_A03_telemetry_failure():
    """A-03: Telemetry Failure - AUDITED (Warning)"""
    telemetry = {"failure_rate": 0.5}
    auditor = AuditMinister()
    result = auditor.audit_telemetry(telemetry)
    assert result["status"] == "AUDITED"
    assert "High failure rate detected." in result["warnings"]


# --- Integration Tests (Simulated) ---

def test_I01_create_dangerous_agent():
    """I-01: Create Dangerous Agent - REJECTED by Guardian"""
    # 1. Spec Designer creates spec (simulated)
    spec_code = 'import os; os.system("rm -rf /")'
    
    # 2. Guardian Scans
    guardian = GuardianMinister(spec_code)
    decision = guardian.get_decision()
    
    assert decision["verdict"] == "BLOCKED"
    assert decision["violation_type"] == "SUBPROCESS"

def test_I02_create_weak_agent():
    """I-02: Create Weak Agent - REJECTED by Validator"""
    spec = {
        "role": "weak_agent",
        "purpose": "Weak.", # Too short
        "dna_rules": [],
        "output_schema": {}
    }
    
    validator = ValidatorMinister()
    result = validator.validate_spec(spec)
    
    assert result["verdict"] == "INVALID"
    assert "Purpose must be at least 20 characters long." in result["issues"]

def test_I03_create_valid_agent():
    """I-03: Create Valid Agent - CREATED"""
    spec = {
        "role": "valid_agent",
        "purpose": "A very useful agent that does important things carefully.",
        "dna_rules": ["Be careful"],
        "output_schema": {"type": "object"}
    }
    # And valid code
    code = 'print("Hello World")'
    
    # Validator
    validator = ValidatorMinister()
    v_res = validator.validate_spec(spec)
    assert v_res["verdict"] == "VALID"
    
    # Guardian
    guardian = GuardianMinister(code)
    g_res = guardian.get_decision()
    assert g_res["verdict"] == "APPROVED"
    
    # Auditor
    auditor = AuditMinister()
    a_res = auditor.audit_spec(spec)
    assert a_res["recommendation"] == "PROCEED"

