import os
import uuid
import logging
from typing import Optional, Dict, Any
from supabase import create_async_client, Client
from .types import EntityType

logger = logging.getLogger(__name__)

class EntityResolver:
    """
    Resolves raw entity handles (names/aliases) to canonical entities.
    Manages alias storage in Supabase.
    """
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.client = create_async_client(url, key)

    async def resolve(self, raw_handle: str) -> Dict[str, Any]:
        """
        Resolve a raw handle to an entity.
        1. Search by canonical name.
        2. Search by alias containment.
        3. Create new entity if not found (optimistic).
        """
        raw_handle = raw_handle.strip()
        
        # 1. Search by canonical name
        try:
            res = await self.client.table("entities")\
                .select("*")\
                .eq("canonical_name", raw_handle)\
                .execute()
            
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error searching canonical name '{raw_handle}': {e}")

        # 2. Search by alias containment
        # JSONB contains check: aliases @> '["handle"]'
        try:
            res = await self.client.table("entities")\
                .select("*")\
                .contains("aliases", f'["{raw_handle}"]')\
                .execute()
            
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.error(f"Error searching alias '{raw_handle}': {e}")

        # 3. Create new entity if not found (Optimistic)
        # Defaulting to SYSTEM type as we don't know enough to classify yet
        new_entity = {
            "canonical_name": raw_handle,
            "aliases": [raw_handle],
            "type": EntityType.SYSTEM.value
        }
        
        try:
            res = await self.client.table("entities")\
                .insert(new_entity)\
                .execute()
            
            if res.data:
                logger.info(f"Created new entity: {raw_handle}")
                return res.data[0]
        except Exception as e:
            # Handle race condition where entity was created between search and insert
            logger.warning(f"Failed to create entity '{raw_handle}', retrying fetch: {e}")
            try:
                res = await self.client.table("entities")\
                    .select("*")\
                    .eq("canonical_name", raw_handle)\
                    .execute()
                if res.data:
                    return res.data[0]
            except Exception as e2:
                logger.error(f"Retry fetch failed for '{raw_handle}': {e2}")
        
        # If all else fails, return a temporary dict structure so caller doesn't crash,
        # but don't persist it.
        return {
            "id": str(uuid.uuid4()),
            "canonical_name": raw_handle,
            "type": "Unresolved"
        }

    async def get_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve entity by UUID."""
        try:
            res = await self.client.table("entities")\
                .select("*")\
                .eq("id", entity_id)\
                .single()\
                .execute()
            return res.data
        except Exception as e:
            logger.error(f"Error retrieving entity {entity_id}: {e}")
            return None

