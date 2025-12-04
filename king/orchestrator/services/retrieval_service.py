"""
Retrieval Service - A governed layer for document retrieval.

- Decides if retrieval is needed (via retriever_agent)
- Fetches from registered sources (e.g., Supabase, Mem0)
- Packages evidence cleanly for agent consumption
- Records telemetry on retrieval effectiveness
"""
from typing import Dict, Any, List
import logging
from agents.agent_runner import AgentRunner
from agents.base_agent import AgentResponse
from services.mem0_tool import search_memory

logger = logging.getLogger(__name__)

def rag_search(query: str, user_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Performs vector search on a knowledge base using Mem0."""
    print(f"[RetrievalService] Executing RAG search for: {query}", flush=True)
    
    try:
        results = search_memory(query=query, user_id=user_id)
        
        # Parse mem0 results
        docs = []
        if isinstance(results, dict) and 'memories' in results:
            for mem in results['memories']:
                docs.append({
                    "content": mem.get("memory", ""),
                    "source": "mem0_knowledge_base",
                    "score": mem.get("score", 0.0)
                })
        elif isinstance(results, list):
             for mem in results:
                docs.append({
                    "content": mem.get("memory", ""),
                    "source": "mem0_knowledge_base",
                    "score": mem.get("score", 0.0)
                })
        
        print(f"[RetrievalService] Found {len(docs)} documents.", flush=True)
        return docs
    except Exception as e:
        print(f"[RetrievalService] RAG search failed: {e}", flush=True)
        return []

def format_docs(raw_docs: List[Dict[str, Any]], max_tokens: int = 1200) -> List[Dict[str, Any]]:
    """
    Formats raw document chunks for agent injection.
    - Trims content to a token limit
    - Ensures proper citation
    """
    chunks = []
    current_tokens = 0
    
    for doc in raw_docs:
        content = doc["content"]
        # Very rough token estimation (4 chars per token)
        est_tokens = len(content) // 4
        
        if current_tokens + est_tokens > max_tokens:
            break
            
        chunks.append({
            "text": content,
            "source": doc["source"]
        })
        current_tokens += est_tokens
        
    return chunks

class RetrievalService:
    def __init__(self):
        self.runner = AgentRunner()

    def run_retrieval(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Orchestrates the full retrieval pipeline.
        1. Call retriever_agent to decide if retrieval is needed.
        2. If so, perform the search.
        3. Format and return the evidence package.
        """
        print(f"[RetrievalService] Analyzing need for retrieval: {query}", flush=True)
        agent_input = {"query": query}
        decision_response: AgentResponse = self.runner.run("retriever_agent", agent_input)

        decision = decision_response.output or {}
        print(f"[RetrievalService] Agent decision: {decision}", flush=True)
        
        needs_retrieval = decision.get("needs_retrieval", False)
        retrieval_query = decision.get("retrieval_query")

        if not needs_retrieval or not retrieval_query:
            return {"enabled": False, "reason": "Retrieval not required by agent."}

        # Perform the actual RAG search
        # Note: We need to pass user_id to search_memory now
        raw_docs = rag_search(retrieval_query, user_id, top_k=3)
        
        if not raw_docs:
            return {"enabled": True, "query": retrieval_query, "docs": [], "source_count": 0, "reason": "No documents found."}

        # Format for clean injection
        docs = format_docs(raw_docs)

        return {
            "enabled": True,
            "query": retrieval_query,
            "docs": docs,
            "source_count": len(docs)
        }
