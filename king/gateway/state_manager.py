import os
import time
import threading
from supabase import create_client, Client
from typing import Optional, Dict, Any

class StateManager:
    _instance = None
    _client: Optional[Client] = None
    _registry_cache: Dict[str, str] = {}
    _registry_last_updated: float = 0
    _spec_cache: Dict[str, Any] = {}
    _spec_last_updated: Dict[str, float] = {}
    
    REGISTRY_TTL = 60  # 60 seconds
    SPEC_TTL = 300     # 5 minutes

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            # Initialize background refresher if needed, but for MVP, lazy refresh on get is simpler/safer
        return cls._instance

    def get_client(self) -> Client:
        """Get or initialize Supabase client."""
        if self._client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not url or not key:
                print("Warning: SUPABASE_URL or SUPABASE_SERVICE_KEY not set.")
                return None
                
            self._client = create_client(url, key)
        return self._client

    def get_agent_url(self, agent_name: str) -> Optional[str]:
        """Fetch agent service URL from registry (with cache)."""
        now = time.time()
        
        # Check cache validity
        if (agent_name in self._registry_cache and 
            (now - self._registry_last_updated) < self.REGISTRY_TTL):
            return self._registry_cache[agent_name]

        # Refresh cache if needed (fetch all active agents to minimize calls)
        client = self.get_client()
        if not client:
            return None

        try:
            # If cache is totally stale or empty, refresh all
            if (now - self._registry_last_updated) >= self.REGISTRY_TTL:
                response = client.table("agent_registry") \
                    .select("agent_name, service_url") \
                    .eq("status", "active") \
                    .execute()
                
                if response.data:
                    self._registry_cache = {
                        item["agent_name"]: item["service_url"] 
                        for item in response.data
                    }
                    self._registry_last_updated = now
            
            return self._registry_cache.get(agent_name)
            
        except Exception as e:
            print(f"Error fetching agent URL: {e}")
            # Return stale data if available
            return self._registry_cache.get(agent_name)

    def get_agent_dna(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Fetch agent DNA specs from DB (with 5-min cache)."""
        now = time.time()
        
        # Check cache
        if (agent_name in self._spec_cache and 
            (now - self._spec_last_updated.get(agent_name, 0)) < self.SPEC_TTL):
            return self._spec_cache[agent_name]

        client = self.get_client()
        if not client:
            return None

        try:
            response = client.table("agent_specs") \
                .select("dna_rules, output_schema") \
                .eq("agent_name", agent_name) \
                .single() \
                .execute()
            
            if response.data:
                self._spec_cache[agent_name] = response.data
                self._spec_last_updated[agent_name] = now
                return response.data
            return None
        except Exception as e:
            print(f"Error fetching DNA for {agent_name}: {e}")
            return self._spec_cache.get(agent_name)

    def log_run(self, agent_name: str, input_data: Dict, output_data: Optional[Dict], 
                success: bool, error: Optional[str] = None, duration_ms: int = 0):
        """Log execution to agent_runs table."""
        client = self.get_client()
        if not client:
            return

        try:
            payload = {
                "agent_name": agent_name,
                "input": input_data,
                "output": output_data,
                "success": success,
                "error": error,
                "duration_ms": duration_ms
            }
            # Fire and forget (in a real app, maybe use background task)
            threading.Thread(target=lambda: client.table("agent_runs").insert(payload).execute()).start()
        except Exception as e:
            print(f"Error logging run: {e}")
