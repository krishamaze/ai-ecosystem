"""
DNA Mutator - Controlled mutation of agent_specs.json with versioning.

Safety guarantees:
- Snapshot full JSON before any mutation
- Validate structure before and after mutation
- File lock to prevent concurrent writes
- Only add_rule and remove_rule supported (modify_rule rejected)
- Schema validation on proposals before apply
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Literal, List
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator
from .supabase_client import supabase
from .agent_dependencies import (
    get_supported_agents,
    run_dependency_health_check,
)


class ChangeType(str, Enum):
    ADD_RULE = "add_rule"
    REMOVE_RULE = "remove_rule"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DnaProposalModel(BaseModel):
    """Strict schema for DNA proposals. Validates before mutation."""

    id: str
    target_role: str
    change_type: ChangeType
    change_content: str = Field(..., min_length=5, max_length=500)
    risk_level: RiskLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    rollback_strategy: str = Field(..., min_length=10)
    status: Literal["approved"]  # Only approved proposals can be validated for apply

    @field_validator("target_role")
    @classmethod
    def validate_target_role(cls, v: str) -> str:
        """Ensure target_role exists AND is supported (has dependency entry)."""
        specs = _load_specs()
        if v not in specs:
            raise ValueError(f"Target role '{v}' does not exist. Valid roles: {list(specs.keys())}")

        # DEPENDENCY CHECK: Only allow mutations to supported agents
        supported = get_supported_agents()
        if v not in supported:
            raise ValueError(
                f"Target role '{v}' is not in AGENT_DEPENDENCIES. "
                f"Add dependency entry before modifying. Supported: {list(supported)}"
            )
        return v

    @field_validator("change_content")
    @classmethod
    def validate_change_content(cls, v: str) -> str:
        """Reject dangerous patterns in rule content."""
        dangerous_patterns = [
            r"ignore\s+(all\s+)?previous",
            r"disregard\s+(all\s+)?instructions",
            r"you\s+are\s+now",
            r"pretend\s+to\s+be",
            r"act\s+as\s+if",
            r"forget\s+(everything|all)",
            r"override\s+rules",
            r"bypass\s+",
            r"<script",
            r"eval\s*\(",
            r"exec\s*\(",
        ]
        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, v_lower):
                raise ValueError(f"Rule contains dangerous pattern: {pattern}")
        return v

    @model_validator(mode="after")
    def validate_risk_confidence_alignment(self):
        """High-risk changes require high confidence."""
        if self.risk_level == RiskLevel.CRITICAL and self.confidence < 0.9:
            raise ValueError("Critical risk proposals require confidence >= 0.9")
        if self.risk_level == RiskLevel.HIGH and self.confidence < 0.75:
            raise ValueError("High risk proposals require confidence >= 0.75")
        return self


def validate_proposal(proposal_data: Dict[str, Any]) -> DnaProposalModel:
    """Validate raw proposal data against schema. Raises ValueError on failure."""
    # Pre-check: System must be healthy before any mutation
    health = run_dependency_health_check()
    if not health["is_healthy"]:
        raise ValueError(f"System dependency health check failed: {health['errors']}")

    try:
        return DnaProposalModel(**proposal_data)
    except Exception as e:
        raise ValueError(f"Proposal validation failed: {str(e)}")

# Cross-platform file locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    import msvcrt

AGENT_SPEC_PATH = Path(__file__).resolve().parent.parent / "agents" / "agent_specs.json"


def _load_specs() -> Dict[str, Any]:
    with open(AGENT_SPEC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _validate_specs(data: Dict[str, Any]) -> None:
    """
    Hard validation: minimal structure check.
    Raise ValueError if invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("agent_specs.json root must be an object")

    for role, spec in data.items():
        if not isinstance(spec, dict):
            raise ValueError(f"Spec for role '{role}' must be an object")

        for key in ("role", "purpose", "output_schema", "dna_rules"):
            if key not in spec:
                raise ValueError(f"Spec for role '{role}' missing key '{key}'")

        if not isinstance(spec["dna_rules"], list):
            raise ValueError(f"'dna_rules' for role '{role}' must be a list")

        if not all(isinstance(r, str) for r in spec["dna_rules"]):
            raise ValueError(f"All dna_rules for role '{role}' must be strings")


def _write_specs_safely(data: Dict[str, Any]) -> None:
    """
    Lock file, write, flush, fsync, unlock.
    Cross-platform: uses fcntl on Linux, msvcrt on Windows.
    """
    with open(AGENT_SPEC_PATH, "r+", encoding="utf-8") as f:
        if HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        else:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        finally:
            if HAS_FCNTL:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            else:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def _snapshot_before_mutation(snapshot: Dict[str, Any], proposal_id: str, applied_by: str) -> str:
    version = f"v{int(datetime.utcnow().timestamp())}"
    supabase.table("dna_versions").insert({
        "version": version,
        "snapshot_json": snapshot,
        "applied_by": applied_by,
        "proposal_id": proposal_id
    }).execute()
    return version


def _apply_single_change(
    specs: Dict[str, Any],
    target_role: str,
    change_type: str,
    change_content: str
) -> Dict[str, Any]:
    if target_role not in specs:
        raise ValueError(f"Target role '{target_role}' not found in agent_specs.json")

    rules = specs[target_role].get("dna_rules", [])

    if change_type == "add_rule":
        if change_content not in rules:
            rules.append(change_content)
        specs[target_role]["dna_rules"] = rules
        return specs

    if change_type == "remove_rule":
        if change_content in rules:
            rules = [r for r in rules if r != change_content]
            specs[target_role]["dna_rules"] = rules
            return specs
        raise ValueError(f"Rule to remove not found for role '{target_role}'")

    if change_type == "modify_rule":
        raise ValueError("modify_rule not supported yet - schema missing target_rule field")

    raise ValueError(f"Unsupported change_type '{change_type}'")


def apply_proposal_mutation(proposal_id: str, approved_by: str) -> Dict[str, Any]:
    """
    Load proposal, validate against schema, snapshot current DNA, apply change, write.
    Returns metadata including new version.
    """
    # 1. Load proposal
    result = supabase.table("dna_proposals").select("*").eq("id", proposal_id).single().execute()
    if not result.data:
        raise ValueError("Proposal not found")

    proposal = result.data

    # 2. SCHEMA VALIDATION - reject invalid proposals before any mutation
    validated = validate_proposal(proposal)

    target_role = validated.target_role
    change_type = validated.change_type.value
    change_content = validated.change_content

    # 3. Load and snapshot current specs
    current_specs = _load_specs()
    _validate_specs(current_specs)

    version = _snapshot_before_mutation(current_specs, proposal_id, approved_by)

    # 4. Apply mutation in-memory
    mutated = _apply_single_change(
        specs=current_specs,
        target_role=target_role,
        change_type=change_type,
        change_content=change_content
    )

    # 5. Validate mutated structure
    _validate_specs(mutated)

    # 6. Commit to disk under lock
    _write_specs_safely(mutated)

    # 7. Mark proposal applied
    supabase.table("dna_proposals").update({
        "status": "applied",
        "applied_at": datetime.utcnow().isoformat()
    }).eq("id", proposal_id).execute()

    # 8. Hot reload agents
    from agents.agent_factory import AgentFactory
    reload_result = AgentFactory.reload()

    return {
        "version": version,
        "target_role": target_role,
        "change_type": change_type,
        "agents_reloaded": reload_result
    }

