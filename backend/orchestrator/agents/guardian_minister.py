import re
import logging
from typing import Dict, Any, List, Tuple
from ..services.guardrails import RequestGuard
from ..services.agent_dependencies import AGENT_DEPENDENCIES

logger = logging.getLogger(__name__)

class GuardianMinister(RequestGuard):
    """
    Guardian Minister: Detects and blocks dangerous patterns in code, prompts, and agent specifications.
    Enforces strict safety in Phase 1.
    """
    
    # Regex patterns from dangerous_patterns.md
    BLOCKLIST_PATTERNS = {
        # File System
        r"open\(.*['\"]w['\"].*\)": ("FILESYSTEM", "File write detected."),
        r"open\(.*['\"]a['\"].*\)": ("FILESYSTEM", "File append detected."),
        r"open\(.*['\"]x['\"].*\)": ("FILESYSTEM", "File create detected."),
        r"os\.remove": ("FILESYSTEM", "File deletion detected."),
        r"os\.rmdir": ("FILESYSTEM", "Directory deletion detected."),
        r"shutil\.rmtree": ("FILESYSTEM", "Recursive directory deletion detected."),
        r"pathlib\.Path\(.*\)\.write_text": ("FILESYSTEM", "Pathlib write detected."),
        
        # Network
        r"import requests": ("NETWORK", "Network library import."),
        r"import urllib": ("NETWORK", "Network library import."),
        r"import socket": ("NETWORK", "Low-level network access."),
        r"import aiohttp": ("NETWORK", "Async network library."),
        r"requests\.get": ("NETWORK", "HTTP GET request."),
        r"requests\.post": ("NETWORK", "HTTP POST request."),
        
        # Subprocess
        r"import subprocess": ("SUBPROCESS", "Subprocess library."),
        r"os\.system": ("SUBPROCESS", "Shell execution."),
        r"os\.popen": ("SUBPROCESS", "Shell execution."),
        r"subprocess\.run": ("SUBPROCESS", "Shell execution."),
        r"exec\(.*\)": ("SUBPROCESS", "Dynamic code execution (high risk)."),
        r"eval\(.*\)": ("SUBPROCESS", "Dynamic code evaluation (high risk)."),
        
        # Database
        r"DROP TABLE": ("DATABASE", "Destructive schema change."),
        r"ALTER TABLE": ("DATABASE", "Schema modification."),
        r"TRUNCATE TABLE": ("DATABASE", "Mass data deletion."),
        r"CREATE TABLE": ("DATABASE", "Unauthorized schema creation."),
        r"information_schema": ("DATABASE", "Schema inspection probing."),
        
        # Environment
        r"os\.environ\[.*\]\s*=": ("ENV_VARS", "Environment variable modification."),
        r"os\.putenv": ("ENV_VARS", "Environment variable modification."),
    }
    
    SECRET_KEYWORDS = ["password", "secret", "api_key", "token", "credential"]

    def __init__(self, content: str = "", user_id: str = "system", context: str = "code"):
        """
        Initialize Guardian.
        :param content: Text to validate (code or output).
        :param user_id: User requesting action.
        :param context: 'code' (default) or 'output'. 
                        'code' skips simple secret keyword checks to allow variable names.
                        'output' enforces strict secret keyword blocking.
        """
        self.context = context
        # Initialize RequestGuard (which runs check_content_safety)
        # We allow empty content if we are just using validate_plan
        super().__init__(content, user_id)
        
        # Initialize Guardian specific fields
        self.verdict = "APPROVED"
        self.risk_level = "LOW"
        self.violation_type = "none"
        self.reason = "Safe"
        
        # Run Guardian specific validation only if content is present
        if content:
            self._validate_patterns()

    def _validate_patterns(self):
        """Run Guardian specific validation logic against blocklist."""
        # If already blocked by RequestGuard base, we might just update our fields or return
        if not self.is_safe:
            self.verdict = "BLOCKED"
            self.risk_level = "CRITICAL"
            self.reason = self.block_reason or "Blocked by base RequestGuard"
            self.violation_type = "safety_filter"
            return

        # Check regex patterns (Always check dangerous code patterns, even in output, to be safe?)
        # Yes, we don't want output to contain executable dangerous code if it's being displayed or processed.
        for pattern, (v_type, reason) in self.BLOCKLIST_PATTERNS.items():
            if re.search(pattern, self.message, re.IGNORECASE):
                self._block(v_type, reason)
                return

        # Check secrets
        # Only check strictly if context is 'output'.
        # In 'code', we assume variable names like 'api_key' are allowed, 
        # unless we implement smarter hardcoded-secret detection.
        if self.context == "output":
            lower_content = self.message.lower()
            for keyword in self.SECRET_KEYWORDS:
                if keyword in lower_content:
                    self._block("secret_leak", f"Contains sensitive keyword: {keyword}")
                    return
    
    def _block(self, violation_type: str, reason: str):
        """Internal helper to set block state."""
        self.is_safe = False
        self.block_reason = reason
        self.verdict = "BLOCKED"
        self.risk_level = "CRITICAL"
        self.violation_type = violation_type
        self.reason = reason
        logger.warning(f"Guardian BLOCKED: {violation_type} - {reason}")

    def get_decision(self) -> Dict[str, Any]:
        """Return structured decision."""
        return {
            "verdict": self.verdict,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "violation_type": self.violation_type
        }

    def validate_plan(self, plan_steps: List[str]) -> Dict[str, Any]:
        """
        Audit a proposed plan for policy violations.
        
        Policies:
        1. Unknown Agent: All agents must exist in AGENT_DEPENDENCIES.
        2. Deployment Safety: 'deploy_code' must be preceded by 'code_reviewer'.
        3. Complexity: Plan length must be <= 10.
        """
        # 1. Complexity Check
        if len(plan_steps) > 10:
            return {
                "verdict": "BLOCKED",
                "risk_level": "HIGH",
                "violation_type": "complexity_limit",
                "reason": f"Plan too long ({len(plan_steps)} steps). Max 10."
            }

        # 2. Unknown Agent Check
        supported_agents = set(AGENT_DEPENDENCIES.keys())
        for agent in plan_steps:
            if agent not in supported_agents:
                return {
                    "verdict": "BLOCKED",
                    "risk_level": "HIGH",
                    "violation_type": "unknown_agent",
                    "reason": f"Plan requests unknown agent: '{agent}'. Creation Council approval required."
                }

        # 3. Deployment Safety Check (Sequence Policy)
        # If 'deploy_code' is present, 'code_reviewer' must appear before it.
        # Note: 'deploy_code' isn't an agent, it's an action. 
        # But if the plan involves 'action_executor' with 'deploy_code', or if we interpret steps as agents...
        # In our system, steps are AGENT ROLES.
        # So we look for specific high-risk agents or sequences.
        # Current agents: code_writer, code_reviewer, video_planner, script_writer.
        # There isn't a "deployer_agent". Deployment is an action triggered via UI or 'action_executor' service.
        # However, if we had a 'deployer_agent', we'd check here.
        # For now, let's enforce: code_writer must be followed by code_reviewer eventually.
        
        if "code_writer" in plan_steps:
            writer_indices = [i for i, x in enumerate(plan_steps) if x == "code_writer"]
            reviewer_indices = [i for i, x in enumerate(plan_steps) if x == "code_reviewer"]
            
            if not reviewer_indices:
                 return {
                    "verdict": "BLOCKED",
                    "risk_level": "CRITICAL",
                    "violation_type": "unsafe_workflow",
                    "reason": "Plan generates code ('code_writer') but lacks 'code_reviewer'."
                }
            
            # Check if any writer appears after all reviewers (bad) or if we just need *one* reviewer after *last* writer?
            # Simplest policy: Last writer must be followed by a reviewer.
            last_writer = writer_indices[-1]
            last_reviewer = reviewer_indices[-1]
            
            if last_reviewer < last_writer:
                 return {
                    "verdict": "BLOCKED",
                    "risk_level": "CRITICAL",
                    "violation_type": "unsafe_workflow",
                    "reason": "Code generation must be followed by review. Found 'code_writer' after last 'code_reviewer'."
                }

        return {
            "verdict": "APPROVED",
            "risk_level": "LOW",
            "violation_type": "none",
            "reason": "Plan policy check passed."
        }
