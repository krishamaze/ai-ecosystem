from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
from typing import Optional, List, Dict, Any

app = FastAPI(title="Script Writer Service")

# Default DNA Rules (Fallback)
DEFAULT_DNA_RULES = [
    "output valid JSON only",
    "must follow context from planner"
]

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not set")
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash-exp")

class ExecuteRequest(BaseModel):
    topic: str
    target_audience: str
    key_message: str
    tone: str
    duration_seconds: int = 60
    context: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "script-writer"}

@app.post("/execute")
async def execute(request: ExecuteRequest):
    """Execute script writer agent logic."""
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
    ROLE: You are a Script Writer for short-form video reels.
    
    DNA RULES (MUST FOLLOW):
    {dna_str}
    
    CONTEXT:
    Topic: {request.topic}
    Audience: {request.target_audience}
    Key Message: {request.key_message}
    Tone: {request.tone}
    Target Duration: {request.duration_seconds} seconds
    
    OUTPUT FORMAT:
    Return strictly valid JSON with the following structure:
    {{
        "confidence": 0.0 to 1.0,
        "script_blocks": [
            {{"time_start": 0, "time_end": 5, "visual": "desc", "audio": "spoken text"}}
        ],
        "duration_seconds": total_int,
        "title": "catchy title"
    }}
    
    IMPORTANT: 
    - Ensure strict JSON validity.
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
            "script_blocks": [],
            "duration_seconds": 0,
            "title": "Error generating script",
            "raw_output": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
