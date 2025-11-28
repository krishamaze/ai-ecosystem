from backend.orchestrator.services.mem0_tool import add_memory

def ingest_sample_data():
    """
    Ingests a sample document into the memory store for RAG testing.
    """
    print("Ingesting sample warranty policy...")
    add_memory(
        user_id="system",
        text="Finetune.Store smartphone warranty lasts 6 months. Physical damage not covered. Bring invoice."
    )
    print("✅ Ingestion complete.")

if __name__ == "__main__":
    ingest_sample_data()

