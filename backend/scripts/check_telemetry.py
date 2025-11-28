import os
import sys
from supabase import create_client, Client
import json

# Ensure we can import backend modules if needed, though mostly using supabase client directly here
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_trace(trace_id=None):
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("Error: credentials missing")
        return

    supabase: Client = create_client(supabase_url, supabase_key)
    
    if trace_id:
        print(f"Checking trace: {trace_id}")
        response = supabase.table("conversation_feedback").select("*").eq("trace_id", trace_id).execute()
    else:
        print("Checking most recent record...")
        response = supabase.table("conversation_feedback").select("*").order("created_at", desc=True).limit(1).execute()
    
    if not response.data:
        print("No record found.")
        return

    record = response.data[0]
    print(json.dumps(record, indent=2))
    
    rag_enabled = record.get("rag_enabled")
    rag_count = record.get("rag_source_count")
    
    if rag_enabled:
        print(f"✅ RAG Enabled. Source Count: {rag_count}")
    else:
        print("❌ RAG NOT Enabled.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        check_trace()
    else:
        check_trace(sys.argv[1])
