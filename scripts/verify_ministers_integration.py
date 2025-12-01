import os
import sys
import json
import time
import uuid
from datetime import datetime

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from orchestrator.services.pipeline_executor import PipelineExecutor
from orchestrator.services.supabase_client import supabase

def create_task_record(title: str) -> str:
    """Create a task record in Supabase and return its ID."""
    print(f"Creating task '{title}'...")
    response = supabase.table("tasks").insert({"title": title}).execute()
    if not response.data:
        raise Exception("Failed to create task record")
    task_id = response.data[0]["id"]
    print(f"✅ Created Task ID: {task_id}")
    return task_id

def verify_telemetry(task_id: str, agent_role: str, expected_success: bool):
    """Check Supabase for telemetry record."""
    print(f"Verifying telemetry for task={task_id}, agent={agent_role}...")
    
    # Allow some time for async writes if any (though currently synchronous)
    time.sleep(1)
    
    response = supabase.table("task_telemetry") \
        .select("*") \
        .eq("task_id", task_id) \
        .eq("agent_role", agent_role) \
        .execute()
    
    if not response.data:
        print(f"❌ No telemetry found for {task_id}")
        return False
        
    record = response.data[0]
    print(f"Found record: ID={record['id']}, Success={record['success']}")
    
    if record['success'] != expected_success:
        print(f"❌ Success mismatch. Expected {expected_success}, got {record['success']}")
        return False
        
    print("✅ Telemetry Verified.")
    return True

def run_integration_tests():
    executor = PipelineExecutor()
    timestamp = int(time.time())
    
    print("\n=== I-01: Create Dangerous Agent (Guardian Block) ===")
    task_id_1 = create_task_record(f"test-I01-{timestamp}")
    input_1 = {
        "code": "import os; os.system('rm -rf /')",
        "context": "code"
    }
    
    # Run Guardian via PipelineExecutor
    result_1 = executor.execute("test_pipeline_1", ["guardian_minister"], input_1, task_id=task_id_1)
    
    # Verify result
    print("Full Result 1:", json.dumps(result_1, indent=2))
    guardian_output = result_1.get("final_output", {})
    print("Guardian Output:", json.dumps(guardian_output, indent=2))
    
    if guardian_output.get("verdict") == "BLOCKED":
        print("✅ Guardian correctly BLOCKED the dangerous code.")
    else:
        print("❌ Guardian FAILED to block dangerous code.")
        
    verify_telemetry(task_id_1, "guardian_minister", True)


    print("\n=== I-02: Create Weak Spec (Validator Invalid) ===")
    task_id_2 = create_task_record(f"test-I02-{timestamp}")
    input_2 = {
        "spec": {
            "role": "weak_agent",
            "purpose": "Too short.",
            "dna_rules": [],
            "output_schema": {}
        }
    }
    
    result_2 = executor.execute("test_pipeline_2", ["validator_minister"], input_2, task_id=task_id_2)
    validator_output = result_2.get("final_output", {})
    print("Validator Output:", json.dumps(validator_output, indent=2))
    
    if validator_output.get("verdict") == "INVALID":
        print("✅ Validator correctly REJECTED weak spec.")
    else:
        print("❌ Validator FAILED to reject weak spec.")

    verify_telemetry(task_id_2, "validator_minister", True)


    print("\n=== I-03: Create Valid Agent (Success) ===")
    task_id_3 = create_task_record(f"test-I03-{timestamp}")
    input_3_val = {
        "spec": {
            "role": "valid_agent",
            "purpose": "A very valid purpose that is definitely long enough.",
            "dna_rules": ["valid"],
            "output_schema": {"type": "object"}
        }
    }
    input_3_guard = {
        "code": "print('Hello Safe World')",
        "context": "code"
    }
    input_3_audit = {
        "spec": input_3_val["spec"]
    }
    
    # We run them sequentially simulating the flow
    # 1. Validator
    print("--- Step 1: Validator ---")
    res_val = executor.execute("test_pipeline_3", ["validator_minister"], input_3_val, task_id=task_id_3)
    if res_val.get("final_output", {}).get("verdict") == "VALID":
        print("✅ Validator Approved.")
    else:
        print("❌ Validator Failed.")

    # 2. Guardian
    print("--- Step 2: Guardian ---")
    res_guard = executor.execute("test_pipeline_3b", ["guardian_minister"], input_3_guard, task_id=task_id_3)
    if res_guard.get("final_output", {}).get("verdict") == "APPROVED":
        print("✅ Guardian Approved.")
    else:
        print("❌ Guardian Failed.")

    # 3. Auditor
    print("--- Step 3: Auditor ---")
    res_audit = executor.execute("test_pipeline_3c", ["audit_minister"], input_3_audit, task_id=task_id_3)
    audit_out = res_audit.get("final_output", {})
    if audit_out.get("status") == "AUDITED":
        print("✅ Auditor Audited.")
        print("Warnings:", audit_out.get("warnings"))
    else:
        print("❌ Auditor Failed.")

    verify_telemetry(task_id_3, "validator_minister", True)
    verify_telemetry(task_id_3, "guardian_minister", True)
    verify_telemetry(task_id_3, "audit_minister", True)

if __name__ == "__main__":
    try:
        run_integration_tests()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
