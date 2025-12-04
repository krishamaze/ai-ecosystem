import json
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ValidatorMinister:
    """
    Validator Minister: Validates the technical structure and feasibility of Agent Specifications.
    """
    
    REQUIRED_FIELDS = ["role", "purpose", "dna_rules", "output_schema"]
    
    def __init__(self):
        pass

    def validate_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an AgentSpec against structural and quality rules.
        """
        issues = []
        suggestions = []
        
        # 1. Structure Validation
        if not isinstance(spec, dict):
            return {
                "verdict": "INVALID",
                "issues": ["Spec must be a JSON object"],
                "suggestions": []
            }

        for field in self.REQUIRED_FIELDS:
            if field not in spec:
                issues.append(f"Missing required field: {field}")
        
        # Check output_schema is valid JSON (it is a dict here)
        if "output_schema" in spec:
            if not isinstance(spec["output_schema"], dict):
                 issues.append("output_schema must be a dictionary.")
            # Basic JSON Schema validation check (heuristic)
            # If it has "type" it should be valid string?
            # V-05: {"type": "invalid"} -> INVALID.
            # We don't have a full JSON schema validator lib installed possibly? 
            # I'll implement basic checks.
            # Just checking if it IS a dict is often enough for "valid JSON structure" if parsed from JSON.
            # But if the schema itself is invalid (e.g. unknown type), we might want to flag it.
            # For now, let's assume if it parses as dict it's "Valid JSON Schema format" structurally.
            # But V-05 says `{"type": "invalid"}` is INVALID.
            # Standard JSON Schema types: string, number, integer, object, array, boolean, null.
            valid_types = ["string", "number", "integer", "object", "array", "boolean", "null"]
            out_schema = spec.get("output_schema", {})
            if isinstance(out_schema, dict):
                # If root has "type", check it
                if "type" in out_schema:
                    if out_schema["type"] not in valid_types:
                        issues.append(f"Invalid JSON Schema type: {out_schema['type']}")
                # Recursive check? For Phase 1 simple check might suffice.
        
        # 2. Purpose Quality
        purpose = spec.get("purpose", "")
        if not isinstance(purpose, str):
            issues.append("Purpose must be a string.")
        elif len(purpose) < 20:
            issues.append("Purpose must be at least 20 characters long.")
        
        # 3. Dependency Check
        # V-06: Refers to non_existent_agent
        # We need a list of valid agents.
        # We can try to import AGENT_DEPENDENCIES or load specs.
        try:
            from services.agent_dependencies import AGENT_DEPENDENCIES
            valid_agents = list(AGENT_DEPENDENCIES.keys())
            
            # Check implicit dependencies in dna_rules or explicit if we add a field?
            # The Spec for Validator says: "Verify that referenced dependencies (other agents or tools) actually exist".
            # Assume spec has 'dependencies' list or we scan text.
            # V-06 implies explicit reference.
            # Let's check if 'dependencies' field exists in spec (not required but if present check).
            # Also check dna_rules for "uses agent X"? Too complex for regex.
            # Let's assume input spec MIGHT have `dependencies` array.
            
            dependencies = spec.get("dependencies", [])
            if isinstance(dependencies, list):
                for dep in dependencies:
                    if dep not in valid_agents:
                        issues.append(f"Dependency not found in registry: {dep}")
                        
        except ImportError:
            logger.warning("Could not import AGENT_DEPENDENCIES for validation")

        verdict = "INVALID" if issues else "VALID"
        
        return {
            "verdict": verdict,
            "issues": issues,
            "suggestions": suggestions
        }

