from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class AuditMinister:
    """
    Audit Minister: Monitors agent telemetry and reviews spec quality metrics.
    Phase 1: Warning-only.
    """
    
    def __init__(self):
        pass

    def audit_spec(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Audit an AgentSpec for quality heuristics.
        """
        warnings = []
        
        # 1. Quality Heuristics
        # Analyze dna_rules for ambiguity
        dna_rules = spec.get("dna_rules", [])
        if isinstance(dna_rules, list):
            for rule in dna_rules:
                rule_lower = str(rule).lower()
                # A-01: "Vague DNA: 'Do good work.'"
                vague_terms = ["good work", "do your best", "try hard", "be nice", "stuff", "things"]
                for term in vague_terms:
                    if term in rule_lower:
                        warnings.append(f"Ambiguous DNA rule detected: '{rule}'")
            
            if len(dna_rules) < 3:
                 warnings.append("Few DNA rules provided. Consider adding more constraints.")
        else:
            warnings.append("dna_rules should be a list.")

        # 2. Blocking Policy (Phase 1)
        # "In Phase 1, the Auditor never blocks an action. It only issues warnings."
        # So we always return AUDITED (or PROCEED as recommendation)
        
        # 3. Telemetry Review (Placeholder for spec audit, real telemetry is handled by run_audit)
        # A-03: "Agent has 50% failure rate." -> Warning.
        # This method audit_spec is for Spec checks. 
        # Telemetry checks would be in a different method or this one if input contains telemetry.
        # The input here is `spec`.
        
        return {
            "status": "AUDITED",
            "warnings": warnings,
            "quality_score": 1.0 if not warnings else 0.8,
            "recommendation": "PROCEED" 
        }

    def audit_telemetry(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze telemetry data.
        """
        warnings = []
        # Check failure rates
        # This mirrors the logic likely intended for the LLM agent but implemented in code for Phase 1/Testing.
        # Or maybe this class is used by the LLM agent as a tool?
        # For now, implementing logic to satisfy tests if they call this class.
        
        # A-03: Agent has 50% failure rate.
        # Assume telemetry_data has "failure_rate" or list of runs.
        if "failure_rate" in telemetry_data:
            if telemetry_data["failure_rate"] >= 0.5:
                warnings.append("High failure rate detected.")
        
        return {
            "status": "AUDITED",
            "warnings": warnings,
            "recommendation": "PROCEED"
        }

