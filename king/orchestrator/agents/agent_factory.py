import json
from pathlib import Path
from datetime import datetime

_spec_path = Path(__file__).parent / "agent_specs.json"

# Mutable state for hot reload
_cache = {
    "specs": None,
    "loaded_at": None
}


def _load_specs() -> dict:
    """Load specs from disk."""
    with open(_spec_path, encoding="utf-8") as f:
        return json.load(f)


def reload_specs() -> dict:
    """Force reload specs from disk. Returns metadata."""
    _cache["specs"] = _load_specs()
    _cache["loaded_at"] = datetime.utcnow().isoformat()
    return {"reloaded_at": _cache["loaded_at"], "agents": list(_cache["specs"].keys())}


def _get_specs() -> dict:
    """Get cached specs, loading if not yet loaded."""
    if _cache["specs"] is None:
        reload_specs()
    return _cache["specs"]


class AgentFactory:
    @staticmethod
    def get_agent(role: str) -> dict:
        spec = _get_specs().get(role)
        if not spec:
            raise ValueError(f"Agent '{role}' not defined")
        return spec

    @staticmethod
    def list_agents() -> list[str]:
        return list(_get_specs().keys())

    @staticmethod
    def reload() -> dict:
        """Hot reload agent specs from disk."""
        return reload_specs()

    @staticmethod
    def generate_prompt(input_data: dict, role: str) -> str:
        spec = AgentFactory.get_agent(role)
        rules = "\n".join(f"- {r}" for r in spec["dna_rules"])
        schema = json.dumps(spec["output_schema"], indent=2)

        return f"""You are {spec['role']}.
Purpose: {spec['purpose']}

INPUT:
{json.dumps(input_data, indent=2)}

RULES:
{rules}

OUTPUT REQUIREMENTS:
- Respond with valid JSON only.
- No markdown.
- No explanation.
- No code fencing.
- Only keys defined in schema.
- Never output text around JSON.

JSON SCHEMA EXACT:
{schema}
"""

