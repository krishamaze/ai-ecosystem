import json
from typing import Optional, Dict, Any
from agents.agent_factory import AgentFactory
from agents.base_agent import AgentResponse
from services.gemini import call_gemini
from agents.guardian_minister import GuardianMinister
from agents.validator_minister import ValidatorMinister
from agents.audit_minister import AuditMinister
from agents.spec_designer import SpecDesignerAgent


class AgentRunner:
    def run(self, role: str, input_data: dict) -> AgentResponse:
        print(f"DEBUG: AgentRunner.run role={role} input={input_data}")
        # --- Deterministic Ministers (Phase 1) & Special Agents ---
        if role == "spec_designer":
            agent = SpecDesignerAgent()
            return agent.run(input_data)

        if role == "guardian_minister":
            content = input_data.get("code") or input_data.get("content") or input_data.get("input", "")
            context = input_data.get("context", "code")
            minister = GuardianMinister(str(content), context=context)
            decision = minister.get_decision()
            return AgentResponse(
                agent=role,
                status="success",
                output=decision,
                confidence=1.0,
                needs_clarification=False
            )
            
        if role == "validator_minister":
            spec = input_data.get("spec") or input_data
            minister = ValidatorMinister()
            decision = minister.validate_spec(spec)
            return AgentResponse(
                agent=role,
                status="success",
                output=decision,
                confidence=1.0,
                needs_clarification=False
            )
            
        if role == "audit_minister":
            minister = AuditMinister()
            if "telemetry" in input_data or "failure_rate" in input_data:
                decision = minister.audit_telemetry(input_data)
            else:
                decision = minister.audit_spec(input_data)
            return AgentResponse(
                agent=role,
                status="success",
                output=decision,
                confidence=1.0,
                needs_clarification=False
            )
        # -----------------------------------------

        prompt = AgentFactory.generate_prompt(input_data, role)

        try:
            raw_output = call_gemini(prompt)
        except Exception as e:
            return AgentResponse(
                agent=role,
                status="error",
                error={"type": "GEMINI_ERROR", "details": str(e)},
                confidence=0.0,
                needs_clarification=True,
                output=None
            )

        # Strip markdown fencing if Gemini still adds it
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return AgentResponse(
                agent=role,
                status="error",
                error={"type": "INVALID_JSON", "raw": raw_output},
                confidence=0.0,
                needs_clarification=True,
                output=None
            )

        return AgentResponse(
            agent=role,
            status="success",
            output=parsed,
            confidence=parsed.get("confidence", 0.5),
            needs_clarification=parsed.get("needs_clarification", False)
        )

    def run_with_memory(
        self,
        role: str,
        input_text: str,
        user_id: str,
        agent_id: Optional[str] = None,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        Run agent with memory-gated context enrichment.

        Flow:
        1. Search raw memories
        2. Filter through memory_selector agent
        3. Build enriched prompt with approved memories only
        4. Execute target agent

        Args:
            role: Target agent role
            input_text: User request text
            user_id: User identifier for memory scoping
            agent_id: Optional agent filter for memories
            top_k: Max candidate memories to retrieve

        Returns:
            Dict with 'response' (AgentResponse), 'memory_used', 'memory_rejected'
        """
        from services.mem0_tool import search_memory, select_memories

        # 1. Retrieve raw memories
        raw_result = search_memory(input_text, user_id, agent_id, limit=top_k)
        raw_memories = raw_result.get("memories", [])

        memory_used = 0
        memory_rejected = 0
        approved = []

        # 2. Filter through memory_selector (skip if no memories)
        if raw_memories:
            selection = select_memories(input_text, raw_memories, user_id)
            approved = selection.get("approved", [])
            memory_used = selection.get("memory_used", 0)
            memory_rejected = selection.get("memory_rejected", 0)

        # 3. Build enriched input
        if approved:
            enriched_input = (
                "Relevant context:\n" +
                "\n".join(f"- {m}" for m in approved) +
                "\n\nCurrent request:\n" +
                input_text
            )
        else:
            enriched_input = input_text

        # 4. Execute target agent
        response = self.run(role, {"input": enriched_input})

        return {
            "response": response,
            "memory_used": memory_used,
            "memory_rejected": memory_rejected
        }

