from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
from typing import Optional, List, Dict, Any

app = FastAPI(title="Code Reviewer Service")

# Default DNA Rules (Fallback)
DEFAULT_DNA_RULES = [
    "output valid JSON only",
    "check for security vulnerabilities"
]

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not set")
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash-exp")

class ExecuteRequest(BaseModel):
    code: str
    language: str = "python"
    context: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "code-reviewer"}

@app.post("/execute")
async def execute(request: ExecuteRequest):
    """Execute code reviewer agent logic."""
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
    ROLE: You are an expert Code Reviewer.
    
    DNA RULES (MUST FOLLOW):
    {dna_str}
    
    CODE TO REVIEW:
    ```{request.language}
    {request.code}
    ```
    
    OUTPUT FORMAT:
    Return strictly valid JSON with the following structure:
    {{
        "verdict": "APPROVE | REQUEST_CHANGES | REJECT",
        "issues": ["Issue 1 (Line X)", "Issue 2 (Line Y)"],
        "security_score": 0.0 to 1.0,
        "quality_score": 0.0 to 1.0,
        "confidence": 0.0 to 1.0,
        "summary": "Brief summary of review",
        "suggested_action": "DEPLOY | STORE_DRAFT | MANUAL_REVIEW"
    }}
    
    IMPORTANT: 
    - Be strict about security.
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
            "verdict": "MANUAL_REVIEW",
            "issues": ["Failed to parse JSON output from reviewer"],
            "security_score": 0.0,
            "quality_score": 0.0,
            "confidence": 0.0,
            "summary": "Review generation failed format check",
            "suggested_action": "MANUAL_REVIEW",
            "raw_output": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
