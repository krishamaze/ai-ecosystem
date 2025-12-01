import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from orchestrator.services.pipeline_executor import PipelineExecutor
from orchestrator.agents.base_agent import AgentResponse

class TestCreationPipeline(unittest.TestCase):
    
    def setUp(self):
        self.executor = PipelineExecutor()
        # Mock the runner inside executor
        self.executor.runner = MagicMock()
        self.executor._record_step_telemetry = MagicMock()
        
    def test_success_path_first_try(self):
        """Test success on first attempt."""
        
        # 1. Designer -> GENERATE
        designer_output = {
            "mode": "GENERATE",
            "spec": {"role": "test_agent", "purpose": "Valid spec", "dna_rules": [], "output_schema": {}}
        }
        
        # 2. Guardian -> APPROVED
        guardian_output = {"verdict": "APPROVED"}
        
        # 3. Validator -> VALID
        validator_output = {"verdict": "VALID"}
        
        self.executor.runner.run.side_effect = [
            AgentResponse(agent="spec_designer", status="success", output=designer_output),
            AgentResponse(agent="guardian_minister", status="success", output=guardian_output),
            AgentResponse(agent="validator_minister", status="success", output=validator_output)
        ]
        
        result = self.executor.execute_creation_pipeline("Create test agent")
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["retries"], 0)
        self.assertEqual(result["final_spec"], designer_output["spec"])
        self.assertEqual(self.executor.runner.run.call_count, 3)

    def test_correction_loop_guardian_block(self):
        """Test loop: Designer -> Guardian Block -> Designer Fix -> Success"""
        
        # Attempt 1
        # Designer 1
        designer_out_1 = {"mode": "GENERATE", "spec": {"role": "dangerous"}}
        # Guardian 1 -> BLOCKED
        guardian_out_1 = {"verdict": "BLOCKED", "violation_type": "files", "reason": "No write"}
        
        # Attempt 2
        # Designer 2 (Fix)
        designer_out_2 = {"mode": "GENERATE", "spec": {"role": "safe"}}
        # Guardian 2 -> APPROVED
        guardian_out_2 = {"verdict": "APPROVED"}
        # Validator 2 -> VALID
        validator_out_2 = {"verdict": "VALID"}
        
        self.executor.runner.run.side_effect = [
            # Try 1
            AgentResponse(agent="spec_designer", status="success", output=designer_out_1),
            AgentResponse(agent="guardian_minister", status="success", output=guardian_out_1),
            # Try 2
            AgentResponse(agent="spec_designer", status="success", output=designer_out_2),
            AgentResponse(agent="guardian_minister", status="success", output=guardian_out_2),
            AgentResponse(agent="validator_minister", status="success", output=validator_out_2)
        ]
        
        result = self.executor.execute_creation_pipeline("Create agent")
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["retries"], 1)
        self.assertEqual(result["final_spec"]["role"], "safe")
        self.assertEqual(self.executor.runner.run.call_count, 5)

    def test_failure_path_max_retries(self):
        """Test failure after max retries."""
        
        # Always fail at Guardian
        designer_out = {"mode": "GENERATE", "spec": {"role": "dangerous"}}
        guardian_out = {"verdict": "BLOCKED", "reason": "Bad"}
        
        # Mock side effect to loop enough times
        # 4 attempts (0, 1, 2, 3) -> 4 * 2 calls = 8 calls
        side_effects = []
        for _ in range(4):
            side_effects.append(AgentResponse(agent="spec_designer", status="success", output=designer_out))
            side_effects.append(AgentResponse(agent="guardian_minister", status="success", output=guardian_out))
            
        self.executor.runner.run.side_effect = side_effects
        
        result = self.executor.execute_creation_pipeline("Create dangerous agent")
        
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Max retries exceeded")
        self.assertEqual(result["retries"], 3) # Loop runs for retries=0,1,2,3 then exits

if __name__ == "__main__":
    unittest.main()



