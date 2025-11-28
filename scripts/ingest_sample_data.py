import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from orchestrator.services.mem0_tool import add_memory
from orchestrator.services.supabase_client import supabase

def ingest_data():
    """
    Ingests sample domain data into Mem0 for RAG testing.
    """
    print("🚀 Ingesting sample domain data...")
    
    # 1. Add Warranty Policy
    result = add_memory(
        messages=[{"role": "assistant", "content": "Finetune.Store smartphone warranty lasts 6 months. Physical damage not covered. Bring invoice."}],
        user_id="system",
        metadata={"category": "policy", "topic": "warranty"}
    )
    
    if result.get("success"):
        print("✅ Warranty policy added successfully.")
    else:
        print(f"❌ Failed to add warranty policy: {result.get('error')}")

    # 2. Add Return Policy
    result = add_memory(
        messages=[{"role": "assistant", "content": "Finetune.Store offers a 30-day return policy on all smartphones. Items must be unused and in original packaging."}],
        user_id="system",
        metadata={"category": "policy", "topic": "return"}
    )
    
    if result.get("success"):
        print("✅ Return policy added successfully.")
    else:
        print(f"❌ Failed to add return policy: {result.get('error')}")

if __name__ == "__main__":
    ingest_data()
