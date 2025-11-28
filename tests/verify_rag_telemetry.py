import requests
import json
import time
import os
import sys
from supabase import create_client, Client
import logging

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("verification_output.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Configuration ---
BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")

if not API_KEY or not SUPABASE_URL:
    logging.error("🔥 FAILURE: SUPABASE_SERVICE_KEY and SUPABASE_URL must be set as environment variables.")
    sys.exit(1)

# --- Supabase Client ---
try:
    supabase: Client = create_client(SUPABASE_URL, API_KEY)
except Exception as e:
    logging.error(f"Error initializing Supabase client: {e}")
    sys.exit(1)

def force_retrieval_trigger():
    """
    Sends a request to /converse that SHOULD trigger RAG.
    """
    endpoint = f"{BASE_URL}/meta/converse"
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": "What is Finetune.Store’s warranty policy for smartphones?",
        "medium": "api",
        "user_id": "test-user-rag-verify"
    }

    logging.info(f"🚀 Sending request to {endpoint}...")
    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        logging.info("✅ Request successful.")
        print(json.dumps(result, indent=2))
        return result.get("trace_id")
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Request failed: {e}")
        return None

def verify_telemetry(trace_id: str):
    """
    Queries task_telemetry (via conversation_feedback join or direct correlation)
    to prove RAG fired.
    """
    logging.info(f"🔍 Checking telemetry for trace_id: {trace_id}...")
    time.sleep(5) # Wait for async writes

    # Check conversation_feedback
    try:
        query = supabase.table("conversation_feedback").select("*").eq("trace_id", trace_id)
        result = query.execute()

        if not result.data:
            logging.error("🔥 FAILURE: No feedback record found.")
            return False

        record = result.data[0]
        logging.info(f"📋 Feedback Record: {json.dumps(record, indent=2)}")

        rag_enabled = record.get("rag_enabled")
        rag_source_count = record.get("rag_source_count")
        rag_query = record.get("rag_query")

        if rag_enabled and rag_source_count and rag_source_count > 0:
            logging.info(f"🎉 SUCCESS: RAG Enabled: {rag_enabled}, Sources: {rag_source_count}, Query: {rag_query}")
            return True
        else:
            logging.error(f"🔥 FAILURE: RAG not triggered. Enabled: {rag_enabled}, Count: {rag_source_count}")
            return False

    except Exception as e:
        logging.error(f"❌ Error checking telemetry: {e}")
        return False

if __name__ == "__main__":
    trace_id = force_retrieval_trigger()
    if trace_id:
        success = verify_telemetry(trace_id)
        if not success:
            sys.exit(1)
    else:
        sys.exit(1)

