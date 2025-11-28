import requests
import json
import time
import os
from supabase import create_client, Client
import logging
import sys

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    supabase = None
    sys.exit(1)

def run_test():
    """
    Sends a request to the /converse endpoint and checks RAG telemetry.
    """
    endpoint = f"{BASE_URL}/meta/converse"
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": "Give return policy for Finetune.Store smartphones.",
        "medium": "api",
        "user_id": "test-user-rag"
    }

    logging.info(f"🚀 Sending request to {endpoint}...")
    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        logging.info("✅ Request successful.")
        print(json.dumps(result, indent=2))
        trace_id = result.get("trace_id")
        return trace_id
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Request failed: {e}")
        return None

def check_telemetry(trace_id: str):
    """
    Checks the telemetry logs for RAG metrics.
    """
    logging.info(f"🔍 Checking telemetry for trace_id: {trace_id}...")
    time.sleep(5)

    try:
        query = supabase.table("conversation_feedback").select("*").eq("trace_id", trace_id)
        result = query.execute()

        if result.data:
            telemetry_entry = result.data[0]
            logging.info("✅ Telemetry entry found.")
            logging.info(json.dumps(telemetry_entry, indent=2))

            rag_enabled = telemetry_entry.get("rag_enabled")
            rag_source_count = telemetry_entry.get("rag_source_count")

            if rag_enabled and rag_source_count > 0:
                logging.info("🎉 SUCCESS: RAG was enabled and sources were found.")
            else:
                logging.error("🔥 FAILURE: RAG telemetry is incorrect.")
                sys.exit(1)
        else:
            logging.error("🔥 FAILURE: No telemetry entry found for the given trace_id.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"❌ An error occurred while checking telemetry: {e}")
        sys.exit(1)

if __name__ == "__main__":
    trace_id = run_test()
    if trace_id:
        check_telemetry(trace_id)
