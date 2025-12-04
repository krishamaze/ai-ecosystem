#!/usr/bin/env python3
"""
Sync agent_specs.json to Supabase agent_specs table.

Usage:
    python -m orchestrator.scripts.sync_specs

Run from backend/ directory with env vars set:
    SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
import json
import os
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from supabase import create_client


def load_specs_from_file() -> dict:
    """Load agent_specs.json from repo."""
    spec_path = Path(__file__).parent.parent / "agents" / "agent_specs.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"agent_specs.json not found at {spec_path}")
    
    with open(spec_path, encoding="utf-8") as f:
        return json.load(f)


def sync_to_supabase(specs: dict, dry_run: bool = False) -> dict:
    """
    Sync specs to Supabase. Upserts on agent_name.
    
    Returns: {"synced": [], "errors": []}
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    
    client = create_client(url, key)
    
    synced = []
    errors = []
    
    for agent_name, spec in specs.items():
        row = {
            "agent_name": agent_name,
            "role": spec.get("role", agent_name),
            "purpose": spec.get("purpose", ""),
            "output_schema": spec.get("output_schema", {}),
            "dna_rules": spec.get("dna_rules", []),
            "is_active": True
        }
        
        if dry_run:
            print(f"[DRY RUN] Would upsert: {agent_name}")
            synced.append(agent_name)
            continue
        
        try:
            # Upsert: insert or update on conflict
            client.table("agent_specs").upsert(
                row,
                on_conflict="agent_name"
            ).execute()
            synced.append(agent_name)
            print(f"✓ Synced: {agent_name}")
        except Exception as e:
            errors.append({"agent": agent_name, "error": str(e)})
            print(f"✗ Failed: {agent_name} - {e}")
    
    return {"synced": synced, "errors": errors}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync agent_specs.json to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be synced")
    args = parser.parse_args()
    
    print("Loading agent_specs.json...")
    specs = load_specs_from_file()
    print(f"Found {len(specs)} agent specs")
    
    print("\nSyncing to Supabase...")
    result = sync_to_supabase(specs, dry_run=args.dry_run)
    
    print(f"\n=== Summary ===")
    print(f"Synced: {len(result['synced'])}")
    print(f"Errors: {len(result['errors'])}")
    
    if result["errors"]:
        print("\nErrors:")
        for err in result["errors"]:
            print(f"  - {err['agent']}: {err['error']}")
        sys.exit(1)
    
    print("\n✓ Sync complete")


if __name__ == "__main__":
    main()

