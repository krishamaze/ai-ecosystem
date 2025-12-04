import json
import os
from typing import ClassVar, Dict, Any, Optional

from agents.base_agent import BaseAgent, AgentResponse
from services.gemini import call_gemini

class SpecDesignerAgent(BaseAgent):
    role: ClassVar[str] = "spec_designer"

    def __init__(self):
        self.dangerous_patterns = self._load_dangerous_patterns()

    def _load_dangerous_patterns(self) -> str:
        """
        Loads the dangerous patterns blocklist from docs/phase1/dangerous_patterns.md.
        """
        try:
            # Assumes the code is running from project root or relative path works
            # Adjust path as necessary based on deployment structure
            # For now, using relative path from workspace root
            path = "docs/phase1/dangerous_patterns.md"
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                return "WARNING: Dangerous patterns file not found. Assume STRICT safety."
        except Exception as e:
            return f"Error loading dangerous patterns: {str(e)}"

    def _build_system_prompt(self) -> str:
        return f"""
You are the **Spec Designer**, the Architect of the AI Kingdom.
Your goal is to translate user requests into precise, executable `AgentSpec` JSON objects.

### CONTEXT & RULES
1. **Architecture Mode (Default):**
   - Analyze the user's request.
   - If vague, ask *one* clarifying question (INTERVIEW mode).
   - If clear, generate the `AgentSpec` (GENERATE mode).

2. **Strict Safety Compliance:**
   - **DO NOT** generate code that violates the Dangerous Patterns Blocklist.
   - **Blocklist Summary:** No file writes, no network calls, no subprocesses/shells, no database schema changes.
   - **Secrets:** Do not include hardcoded secrets.

3. **Output Schema Compliance:**
   - You must output pure JSON.
   - Do not wrap in markdown code blocks (e.g., ```json ... ```).
   - The JSON must strictly follow the schema below.

### DANGEROUS PATTERNS BLOCKLIST
{self.dangerous_patterns}

### OUTPUT SCHEMAS

#### 1. INTERVIEW MODE (Use if request is vague)
{{
  "mode": "INTERVIEW",
  "question": "To create this specialist, I need to know: [Specific Question]"
}}

#### 2. GENERATE MODE (Use if request is clear)
{{
  "mode": "GENERATE",
  "spec": {{
    "role": "snake_case_unique_name",
    "purpose": "Detailed description (>20 chars)...",
    "dna_rules": [
      "Rule 1: Detailed instruction",
      "Rule 2: Safety constraint"
    ],
    "output_schema": {{
      "type": "object",
      "properties": {{ ... }}
    }},
    "dependencies": ["list_of_existing_agents_or_tools"]
  }}
}}

### INSTRUCTIONS
- If the user provides a "Minister Error" or "Block Reason", you are in **Correction Mode**. Fix the issue in the spec.
- Ensure `purpose` is > 20 characters.
- Ensure `output_schema` is valid JSON Schema.
- Reply ONLY with the JSON object.
"""

    def run(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Process the input and return an AgentResponse.
        input_data expected keys:
        - request: The user's request string.
        - context: (Optional) Previous errors or context.
        """
        user_request = input_data.get("request", "")
        context = input_data.get("context", "")
        
        if not user_request:
             return AgentResponse(
                agent=self.role,
                status="error",
                error={"type": "MISSING_INPUT", "details": "No request provided."},
                confidence=0.0,
                needs_clarification=True
            )

        prompt = f"""
{self._build_system_prompt()}

USER REQUEST:
"{user_request}"

CONTEXT / PREVIOUS ERRORS:
"{context}"

YOUR JSON RESPONSE:
"""
        try:
            # Call LLM
            raw_response = call_gemini(prompt)
            
            # Clean response (remove markdown if present)
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            # Parse JSON
            parsed_output = json.loads(cleaned_response)
            
            # Determine status based on mode
            mode = parsed_output.get("mode", "UNKNOWN")
            status = "completed" if mode == "GENERATE" else "clarification_needed"
            
            return AgentResponse(
                agent=self.role,
                status=status,
                output=parsed_output,
                confidence=1.0, # Placeholder
                needs_clarification=(mode == "INTERVIEW")
            )

        except json.JSONDecodeError:
            return AgentResponse(
                agent=self.role,
                status="error",
                error={"type": "INVALID_JSON", "details": f"LLM produced invalid JSON: {raw_response[:100]}..."},
                confidence=0.0,
                needs_clarification=False
            )
        except Exception as e:
            return AgentResponse(
                agent=self.role,
                status="error",
                error={"type": "PROCESSING_ERROR", "details": str(e)},
                confidence=0.0,
                needs_clarification=False
            )

