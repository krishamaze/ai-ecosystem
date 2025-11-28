import unittest
import os
import sys
import uuid
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

# Ensure /app is in path so we can import 'orchestrator'
sys.path.append('/app')

try:
    from orchestrator.services.mem0_tool import add_memory, search_memory
except ImportError:
    # Fallback/Debug if the above fails
    print(f"Current sys.path: {sys.path}", flush=True)
    try:
        from backend.orchestrator.services.mem0_tool import add_memory, search_memory
    except ImportError as e:
        print(f"Import failed: {e}", flush=True)
        raise e

class Mem0ValidationTest(unittest.TestCase):

    def setUp(self):
        """Set up the Supabase client for telemetry checks."""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        if not self.supabase_url or not self.supabase_key:
            self.fail("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def test_add_memory_returns_id(self):
        """Test that adding a memory returns a valid memory object with an ID."""
        print("\n--- Running test_add_memory_returns_id ---", flush=True)
        try:
            result = add_memory(
                user_id="test_user_validation",
                text="Finetune.Store smartphone warranty lasts 6 months."
            )
        except TypeError:
             # Fallback if the API expects messages list
             result = add_memory(
                user_id="test_user_validation",
                messages=[{"role": "user", "content": "Finetune.Store smartphone warranty lasts 6 months."}]
            )
            
        print(f"add_memory result: {result}", flush=True)
        self.assertIsNotNone(result)
        # Check for success/id depending on return shape
        self.assertTrue(result.get("success") or 'id' in result, "add_memory failed")

    def test_search_retrieves_known_content(self):
        """Test that searching for a known term retrieves the relevant memory."""
        print("\n--- Running test_search_retrieves_known_content ---", flush=True)
        
        # Retry loop to handle asynchronous indexing
        max_retries = 5
        retry_delay = 2  # seconds
        
        search_results = []
        for i in range(max_retries):
            print(f"Attempt {i+1}/{max_retries}...", flush=True)
            search_results = search_memory(
                query="warranty policy",
                user_id="test_user_validation"
            )
            print(f"search_memory result: {search_results}", flush=True)
            
            # Check for non-empty results
            if isinstance(search_results, list) and len(search_results) > 0:
                break
            if isinstance(search_results, dict) and len(search_results.get('memories', [])) > 0:
                break
            
            if i < max_retries - 1:
                time.sleep(retry_delay)
        
        self.assertIsNotNone(search_results)
        
        # Validate based on return type
        memories = []
        if isinstance(search_results, dict):
            memories = search_results.get('memories', [])
        elif isinstance(search_results, list):
            memories = search_results
            
        self.assertGreater(len(memories), 0, "Search did not return any results after retries.")
        
        # Check content match
        found_text = any("warranty" in str(m).lower() for m in memories)
        self.assertTrue(found_text, "Warranty text not found in search results")

    def test_telemetry_writes(self):
        """Test that a telemetry record can be written and read back."""
        print("\n--- Running test_telemetry_writes ---", flush=True)
        test_trace_id = str(uuid.uuid4())
        
        # Insert a dummy record
        insert_data = {
            "trace_id": test_trace_id,
            "user_id": "test_telemetry_user",
            "message_hash": "dummy_hash",
            "intent": "test_intent",
            "success": True
        }
        insert_result = self.supabase.table("conversation_feedback").insert(insert_data).execute()
        
        self.assertEqual(len(insert_result.data), 1, "Failed to insert telemetry record.")

        # Query for the record
        query_result = self.supabase.table("conversation_feedback").select("*").eq("trace_id", test_trace_id).execute()
        
        self.assertEqual(len(query_result.data), 1, "Failed to query telemetry record.")
        self.assertEqual(query_result.data[0]["trace_id"], test_trace_id)
        print("✅ Telemetry write and read successful.", flush=True)

if __name__ == '__main__':
    unittest.main()
