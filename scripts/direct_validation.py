import os
import sys
from supabase import create_client, Client
from datetime import datetime

# This is a hack to allow the test to run from the root directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.orchestrator.services.mem0_tool import add_memory, search_memory

def run_validation():
    """
    Directly calls the mem0 and telemetry functions to validate their functionality.
    """
    print("--- Starting Direct Validation ---")

    # --- Test add_memory ---
    print("\n--- Testing add_memory ---")
    add_result = add_memory(
        user_id="direct_test_user",
        text="Direct test: Finetune.Store warranty is 12 months for parts and labor."
    )
    print(f"add_memory result: {add_result}")
    assert add_result and 'id' in add_result, "add_memory failed."

    # --- Test search_memory ---
    print("\n--- Testing search_memory ---")
    search_results = search_memory(
        query="warranty",
        user_id="direct_test_user"
    )
    print(f"search_memory result: {search_results}")
    assert search_results and len(search_results) > 0, "search_memory failed."

    # --- Test Telemetry ---
    print("\n--- Testing Telemetry ---")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        print("🔥 FAILURE: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        return

    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        test_trace_id = f"direct-test-{datetime.now().isoformat()}"
        
        insert_data = {
            "trace_id": test_trace_id,
            "user_id": "direct_telemetry_user",
            "message_hash": "direct_dummy_hash",
            "intent": "direct_test_intent",
            "success": True
        }
        
        insert_result = supabase.table("conversation_feedback").insert(insert_data).execute()
        
        if insert_result.data:
            print("✅ Telemetry insert successful.")
        else:
            print("🔥 FAILURE: Telemetry insert failed.")
            return

        query_result = supabase.table("conversation_feedback").select("*").eq("trace_id", test_trace_id).execute()
        
        if query_result.data:
            print("✅ Telemetry query successful.")
            print(f"Query result: {query_result.data[0]}")
        else:
            print("🔥 FAILURE: Telemetry query failed.")

    except Exception as e:
        print(f"🔥 FAILURE: An error occurred during telemetry test: {e}")

    print("\n--- Direct Validation Finished ---")

if __name__ == "__main__":
    run_validation()

