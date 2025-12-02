from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
import time
from typing import Optional, List, Dict, Any

app = FastAPI(title="Video Planner Service")

# Default DNA Rules (Fallback)
DEFAULT_DNA_RULES = [
    "output valid JSON only",
    "only ask ONE question at a time"
]

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not set")
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash-exp")

class ExecuteRequest(BaseModel):
    user_input: str
    known_context: Dict[str, Any] = {}
    missing_fields: List[str] = ["topic", "target_audience", "key_message", "tone"]
    context: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "video-planner"}

@app.post("/execute")
async def execute(request: ExecuteRequest):
    """Execute video planner agent logic."""
    if not os.getenv("GEMINI_API_KEY"):
         raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    # 1. Determine DNA Rules
    dna_rules = DEFAULT_DNA_RULES
    if request.context and "dna_rules" in request.context:
        dna_rules = request.context["dna_rules"]
    else:
        try:
            if os.path.exists("dna_rules.json"):
                with open("dna_rules.json", "r") as f:
                    dna_rules = json.load(f)
        except Exception:
            pass

    # Build Prompt
    dna_str = "\n".join([f"- {rule}" for rule in dna_rules])
    
    prompt = f"""
    ROLE: You are a Video Planner. Your goal is to gather all missing fields.
    
    DNA RULES (MUST FOLLOW):
    {dna_str}
    
    CURRENT STATUS:
    User Input: "{request.user_input}"
    Known Context: {json.dumps(request.known_context)}
    Missing Fields: {json.dumps(request.missing_fields)}
    
    OUTPUT FORMAT:
    Return strictly valid JSON with the following structure:
    {{
        "confidence": 0.0 to 1.0,
        "known_context": {{updated key-values}},
        "missing_fields": ["remaining", "fields"],
        "current_question": "Question to ask user (or null if done)",
        "needs_clarification": boolean,
        "timestamp": "{time.time()}"
    }}
    
    IMPORTANT: 
    - Only ask ONE question at a time.
    - If user input answers a missing field, move it to known_context.
    - Return strict JSON.
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        # Clean markdown if present
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        return json.loads(text)
        
    except json.JSONDecodeError:
        return {
            "confidence": 0.0,
            "known_context": request.known_context,
            "missing_fields": request.missing_fields,
            "current_question": "I couldn't understand that. Could you repeat?",
            "needs_clarification": True,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
