"""
Agent Dependency Map - Defines valid agent relationships and validates system viability.

Enforces:
- No circular handoffs
- No phantom dependencies (agents depending on non-existent roles)
- No orphan agents (new agents must declare dependencies)
"""

from typing import Dict, List, Set, Tuple
from pathlib import Path
import json

AGENT_SPEC_PATH = Path(__file__).resolve().parent.parent / "agents" / "agent_specs.json"

# Canonical dependency map: agent -> list of agents it can call
# This is the single source of truth for agent interoperability
AGENT_DEPENDENCIES: Dict[str, List[str]] = {
    # Content pipeline
    "video_planner": ["script_writer"],           # Planner hands off to writer
    "script_writer": [],                          # Writer is terminal (produces output)

    # Code pipeline
    "code_writer": ["code_reviewer"],             # Writer submits to reviewer
    "code_reviewer": [],                          # Reviewer is terminal (verdict)

    # Meta layer (can observe all agents)
    "audit_minister": ["video_planner", "script_writer", "code_writer", "code_reviewer"],
    "meta_reasoner": ["audit_minister"],          # Meta-reasoner reads from auditor only
    
    # Ministers (System Guardrails)
    "guardian_minister": [],                      # Gatekeeper (no downstream)
    "validator_minister": [],                     # Gatekeeper (no downstream)

    # Constitutional Layer
    "ambedkar": [],                               # Constitutional Architect (terminal, doc output)

    # Helpers (used internally or as tools)
    "memory_selector": [],
    "retriever_agent": [],
    "planner_agent": [],
}


def _load_specs() -> Dict:
    """Load current agent specs."""
    with open(AGENT_SPEC_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_registered_agents() -> Set[str]:
    """Return set of all agents defined in agent_specs.json."""
    return set(_load_specs().keys())


def get_supported_agents() -> Set[str]:
    """Return set of agents that have defined dependencies (system-supported)."""
    return set(AGENT_DEPENDENCIES.keys())


def validate_no_circular_deps() -> Tuple[bool, str]:
    """
    Detect circular dependencies using DFS.
    Returns (is_valid, error_message).
    """
    def dfs(node: str, visited: Set[str], path: Set[str]) -> Tuple[bool, List[str]]:
        if node in path:
            return False, list(path) + [node]
        if node in visited:
            return True, []
        
        visited.add(node)
        path.add(node)
        
        for dep in AGENT_DEPENDENCIES.get(node, []):
            valid, cycle = dfs(dep, visited, path)
            if not valid:
                return False, cycle
        
        path.remove(node)
        return True, []
    
    visited: Set[str] = set()
    for agent in AGENT_DEPENDENCIES:
        valid, cycle = dfs(agent, visited, set())
        if not valid:
            return False, f"Circular dependency detected: {' -> '.join(cycle)}"
    
    return True, ""


def validate_no_phantom_deps() -> Tuple[bool, str]:
    """
    Ensure all dependencies reference existing agents.
    Returns (is_valid, error_message).
    """
    registered = get_all_registered_agents()
    supported = get_supported_agents()
    
    phantoms = []
    for agent, deps in AGENT_DEPENDENCIES.items():
        for dep in deps:
            if dep not in registered:
                phantoms.append(f"{agent} -> {dep} (not in agent_specs.json)")
            elif dep not in supported:
                phantoms.append(f"{agent} -> {dep} (not in AGENT_DEPENDENCIES)")
    
    if phantoms:
        return False, f"Phantom dependencies: {phantoms}"
    return True, ""


def validate_agents_have_deps() -> Tuple[bool, str]:
    """
    Ensure all registered agents have dependency entries.
    Returns (is_valid, error_message).
    """
    registered = get_all_registered_agents()
    supported = get_supported_agents()
    
    orphans = registered - supported
    if orphans:
        return False, f"Orphan agents (no dependency entry): {list(orphans)}"
    return True, ""


def run_dependency_health_check() -> Dict:
    """
    Run all dependency validations.
    Returns status dict with is_healthy flag and any errors.
    """
    checks = {
        "no_circular": validate_no_circular_deps(),
        "no_phantom": validate_no_phantom_deps(),
        "all_have_deps": validate_agents_have_deps(),
    }
    
    errors = []
    for name, (valid, msg) in checks.items():
        if not valid:
            errors.append(f"{name}: {msg}")
    
    return {
        "is_healthy": len(errors) == 0,
        "errors": errors,
        "registered_agents": list(get_all_registered_agents()),
        "supported_agents": list(get_supported_agents()),
    }


def validate_agent_can_call(caller: str, callee: str) -> bool:
    """Check if caller agent is allowed to invoke callee agent."""
    return callee in AGENT_DEPENDENCIES.get(caller, [])


def get_dependency_graph_mermaid() -> str:
    """Generate Mermaid diagram syntax for dependency visualization."""
    lines = ["graph TD"]
    
    for agent, deps in AGENT_DEPENDENCIES.items():
        if not deps:
            lines.append(f"    {agent}[{agent}]:::terminal")
        for dep in deps:
            lines.append(f"    {agent} --> {dep}")
    
    lines.append("")
    lines.append("    classDef terminal fill:#90EE90,stroke:#228B22")
    
    return "\n".join(lines)

