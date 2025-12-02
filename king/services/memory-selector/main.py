from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
from typing import Optional, List, Dict, Any

app = FastAPI(title="Memory Selector Service")

# Default DNA Rules (Fallback)
DEFAULT_DNA_RULES = [
    "output valid JSON only",
    "Approve only memories that directly aid the current request"
]

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not set")
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash-exp")

class ExecuteRequest(BaseModel):
    query: str
    candidate_memories: List[Dict[str, Any]]
    context: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "memory-selector"}

@app.post("/execute")
async def execute(request: ExecuteRequest):
    """Execute memory selector agent logic."""
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
    ROLE: You are a Memory Selector. Filter noise from retrieved memories.
    
    DNA RULES (MUST FOLLOW):
    {dna_str}
    
    USER QUERY:
    "{request.query}"
    
    CANDIDATE MEMORIES:
    {json.dumps(request.candidate_memories)}
    
    OUTPUT FORMAT:
    Return strictly valid JSON with the following structure:
    {{
        "approved_memories": ["mem1", "mem2"],
        "rejected_memories": ["mem3"],
        "confidence": 0.0 to 1.0
    }}
    
    IMPORTANT: 
    - Only approve memories relevant to the query.
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
            "approved_memories": [],
            "rejected_memories": [],
            "confidence": 0.0,
            "error": "JSON parse error",
            "raw_output": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

