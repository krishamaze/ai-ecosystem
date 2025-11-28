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
BASE_URL = "http://localhost:8000"  # Replace with your actual API URL
API_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")

logging.info(f"SUPABASE_URL: {SUPABASE_URL}")
logging.info(f"API_KEY: {API_KEY}")

if not API_KEY or not SUPABASE_URL:
    logging.error("🔥 FAILURE: SUPABASE_KEY and SUPABASE_URL must be set as environment variables.")
    sys.exit(1)

# --- Supabase Client ---
try:
    supabase: Client = create_client(SUPABASE_URL, API_KEY)
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    supabase = None

def run_test():
    """
    Sends a request to the /converse endpoint and checks telemetry.
    """
    endpoint = f"{BASE_URL}/meta/converse"
    headers = {"Content-Type": "application/json"}
    payload = {
        "message": "Generate 30-sec reel about Finetune festive offer",
        "medium": "api",
        "user_id": "test-user-memory"
    }

    print(f"🚀 Sending request to {endpoint}...")
    try:
        response = requests.post(endpoint, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        print("✅ Request successful.")
        print("Response:", json.dumps(result, indent=2))
        trace_id = result.get("trace_id")
        return trace_id
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def check_telemetry(trace_id: str):
    """
    Checks the telemetry logs for memory_used > 0.
    """
    if not supabase:
        logging.warning("Supabase client not initialized. Skipping telemetry check.")
        return

    logging.info(f"🔍 Checking telemetry for trace_id: {trace_id}...")
    time.sleep(5)  # Allow time for telemetry to be processed

    try:
        query = supabase.table("conversation_feedback").select("*").eq("trace_id", trace_id)
        result = query.execute()

        if result.data:
            telemetry_entry = result.data[0]
            logging.info("✅ Telemetry entry found.")
            logging.info(json.dumps(telemetry_entry, indent=2))

            # --- Verification ---
            memory_used = telemetry_entry.get("memory_used")
            if memory_used:
                logging.info("🎉 SUCCESS: `memory_used` is true.")
            else:
                logging.error("🔥 FAILURE: `memory_used` is false or not present.")
        else:
            logging.error("🔥 FAILURE: No telemetry entry found for the given trace_id.")
    except Exception as e:
        logging.error(f"❌ An error occurred while checking telemetry: {e}")

if __name__ == "__main__":
    print("--- Starting Test ---")
    trace_id = run_test()
    if trace_id:
        check_telemetry(trace_id)
    print("--- Test Finished ---")
