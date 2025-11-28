from .base_agent import BaseAgent, AgentResponse

class VideoPlannerAgent(BaseAgent):
    role = "video_planner"

    def run(self, input_data: dict) -> AgentResponse:
        # If no context yet — ask first question
        known_context = input_data.get("known_context", {})

        if not known_context:
            response = {
                "agent": self.role,
                "status": "question",
                "output": {
                    "current_question": "What is the main purpose of this video?",
                    "known_context": {},
                    "missing_fields": [
                        "goal",
                        "target_audience",
                        "duration",
                        "tone",
                        "story_style",
                        "CTA",
                        "asset_list",
                        "language",
                        "platform",
                        "visual_rules",
                        "constraints"
                    ]
                },
                "confidence": 0.4,
                "needs_clarification": True
            }
            return self.validate_response(response)

        # TODO: Next iteration logic (will be expanded later)
        response = {
            "agent": self.role,
            "status": "pending",
            "output": known_context,
            "confidence": 0.5,
            "needs_clarification": True
        }
        return self.validate_response(response)

