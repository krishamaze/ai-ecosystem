import os
import json
from supabase import create_client, Client

API_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")

try:
    supabase: Client = create_client(SUPABASE_URL, API_KEY)
    
    # Query the last 5 telemetry records
    response = supabase.table("task_telemetry").select("rag_enabled, rag_source_count, rag_query, trace_id").order("created_at", desc=True).limit(5).execute()
    
    with open("db_result.txt", "w") as f:
        f.write(json.dumps(response.data, indent=2))
        
except Exception as e:
    with open("db_result.txt", "w") as f:
        f.write(f"Error: {str(e)}")

