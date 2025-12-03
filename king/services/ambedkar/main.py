from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
from typing import Optional, List, Dict, Any

app = FastAPI(title="Ambedkar - Constitutional Architect")

# Load DNA Rules
try:
    with open("dna_rules.json", "r") as f:
        DNA_RULES = json.load(f)
except FileNotFoundError:
    DNA_RULES = ["uphold the constitution"]

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
else:
    model = None

class ExecuteRequest(BaseModel):
    task: str  # e.g., "Update history with Mem0 deployment" or "Review this architecture proposal"
    context: Optional[Dict[str, Any]] = None # Current doc content or diffs
    user_id: Optional[str] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ambedkar"}

@app.post("/execute")
async def execute(request: ExecuteRequest):
    """Execute Ambedkar logic."""
    if not model:
         raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    dna_str = "\n".join([f"- {rule}" for rule in DNA_RULES])
    
    prompt = f"""
    ROLE: You are Ambedkar, the Constitutional Architect of the KINGDOM.
    
    DNA RULES (SUPREME LAW):
    {dna_str}
    
    TASK:
    {request.task}
    
    CONTEXT:
    {json.dumps(request.context, default=str) if request.context else "None"}
    
    OUTPUT FORMAT:
    Return strictly valid JSON with the following structure:
    {{
        "verdict": "APPROVED | REJECTED | AMENDMENT_REQUIRED",
        "reasoning": "Constitutional justification based on Articles I-IV",
        "updates": [
            {{
                "file_path": "docs/...",
                "action": "overwrite | append",
                "content": "Markdown content..."
            }}
        ],
        "confidence": 0.0 to 1.0
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ambedkar logic failed: {str(e)}")

