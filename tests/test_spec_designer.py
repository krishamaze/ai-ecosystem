import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.orchestrator.agents.spec_designer import SpecDesignerAgent

class TestSpecDesignerAgent(unittest.TestCase):

    def setUp(self):
        self.agent = SpecDesignerAgent()

    @patch('backend.orchestrator.agents.spec_designer.call_gemini')
    def test_interview_mode_trigger(self, mock_gemini):
        """Test that the agent returns INTERVIEW mode when the LLM decides clarification is needed."""
        
        # Mock LLM response
        mock_response = json.dumps({
            "mode": "INTERVIEW",
            "question": "What tools should the agent use?"
        })
        mock_gemini.return_value = mock_response

        input_data = {"request": "Create an agent."}
        response = self.agent.run(input_data)

        self.assertEqual(response.status, "clarification_needed")
        self.assertTrue(response.needs_clarification)
        self.assertEqual(response.output["mode"], "INTERVIEW")
        self.assertEqual(response.output["question"], "What tools should the agent use?")

    @patch('backend.orchestrator.agents.spec_designer.call_gemini')
    def test_generate_mode_trigger(self, mock_gemini):
        """Test that the agent returns GENERATE mode with a valid spec."""
        
        # Mock LLM response
        mock_response = json.dumps({
            "mode": "GENERATE",
            "spec": {
                "role": "weather_reporter",
                "purpose": "Reports weather for a given location",
                "dna_rules": ["Be accurate"],
                "output_schema": {"type": "object"},
                "dependencies": []
            }
        })
        mock_gemini.return_value = mock_response

        input_data = {"request": "Create a weather reporter agent."}
        response = self.agent.run(input_data)

        self.assertEqual(response.status, "completed")
        self.assertFalse(response.needs_clarification)
        self.assertEqual(response.output["mode"], "GENERATE")
        self.assertEqual(response.output["spec"]["role"], "weather_reporter")

    @patch('backend.orchestrator.agents.spec_designer.call_gemini')
    def test_clean_markdown_response(self, mock_gemini):
        """Test that the agent correctly strips markdown code blocks."""
        
        # Mock LLM response with markdown
        mock_response = """
        ```json
        {
            "mode": "GENERATE",
            "spec": {
                "role": "clean_agent"
            }
        }
        ```
        """
        mock_gemini.return_value = mock_response

        input_data = {"request": "Create an agent."}
        response = self.agent.run(input_data)

        self.assertEqual(response.status, "completed")
        self.assertEqual(response.output["spec"]["role"], "clean_agent")

    def test_dangerous_patterns_injection(self):
        """Test that dangerous patterns are loaded and injected into the system prompt."""
        
        # Ensure the file loading logic worked (or fell back gracefully)
        # We can't strictly assert content unless we know the file exists, 
        # but we can check it's part of the prompt.
        
        prompt = self.agent._build_system_prompt()
        self.assertIn("DANGEROUS PATTERNS BLOCKLIST", prompt)
        
        # Check for a specific known pattern from the file if it exists
        if os.path.exists("docs/phase1/dangerous_patterns.md"):
            with open("docs/phase1/dangerous_patterns.md", "r") as f:
                content = f.read()
                # Grab a snippet to verify
                snippet = "os.remove" 
                if snippet in content:
                    self.assertIn(snippet, prompt)

    @patch('backend.orchestrator.agents.spec_designer.call_gemini')
    def test_invalid_json_handling(self, mock_gemini):
        """Test handling of invalid JSON from LLM."""
        
        mock_gemini.return_value = "This is not JSON."
        
        input_data = {"request": "Create an agent."}
        response = self.agent.run(input_data)
        
        self.assertEqual(response.status, "error")
        self.assertEqual(response.error["type"], "INVALID_JSON")

if __name__ == '__main__':
    unittest.main()

