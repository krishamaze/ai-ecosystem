import os
import sys

# Add the backend directory to the python path so we can import mem0_tool
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from orchestrator.services.mem0_tool import add_memory
except ImportError as e:
    print(f"Error importing mem0_tool: {e}")
    sys.exit(1)

def ingest_data():
    print("🚀 Ingesting domain data into Mem0...")
    
    # Ingest Finetune.Store warranty policy
    policy_text = "Finetune.Store smartphone warranty lasts 6 months. Physical damage not covered. Bring invoice."
    user_id = "test-user-rag" # Using the same user_id as the test script
    
    result = add_memory(
        messages=[{"role": "user", "content": policy_text}],
        user_id=user_id,
        metadata={"source": "Finetune.Store SOP", "category": "policy"}
    )
    
    if result.get("success"):
        print("✅ Domain data ingested successfully.")
        print(f"Result: {result}")
    else:
        print("❌ Failed to ingest domain data.")
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    if not os.getenv("MEM0_API_KEY"):
        print("❌ MEM0_API_KEY environment variable not set.")
        sys.exit(1)
    ingest_data()

