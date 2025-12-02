from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
import json
from typing import Optional, List, Dict, Any

app = FastAPI(title="Code Writer Service")

# Default DNA Rules (Fallback)
DEFAULT_DNA_RULES = [
    "output code ONLY in specified language",
    "every function must have docstring",
    "include basic error handling",
    "output valid JSON only"
]

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not set")
    # For build phase, don't crash, but runtime will fail
else:
    genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.0-flash-exp")

class ExecuteRequest(BaseModel):
    task: str
    language: str = "python"
    context: Optional[Dict[str, Any]] = None

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "code-writer", "model": "gemini-2.0-flash-exp"}

@app.post("/execute")
async def execute(request: ExecuteRequest):
    """Execute code writer agent logic."""
    if not os.getenv("GEMINI_API_KEY"):
         raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    # 1. Determine DNA Rules
    # Priority: Context Injection (from Gateway) > Local JSON > Hardcoded Defaults
    dna_rules = DEFAULT_DNA_RULES
    
    # Check context for injected DNA
    if request.context and "dna_rules" in request.context:
        dna_rules = request.context["dna_rules"]
    else:
        # Check local file
        try:
            if os.path.exists("dna_rules.json"):
                with open("dna_rules.json", "r") as f:
                    dna_rules = json.load(f)
        except Exception:
            pass

    # Build Prompt
    dna_str = "\n".join([f"- {rule}" for rule in dna_rules])
    
    prompt = f"""
    ROLE: You are an expert Code Writer.
    
    DNA RULES (MUST FOLLOW):
    {dna_str}
    
    TASK:
    {request.task}
    
    LANGUAGE: {request.language}
    
    CONTEXT:
    {json.dumps(request.context) if request.context else "None"}
    
    OUTPUT FORMAT:
    Return strictly valid JSON with the following structure:
    {{
        "language": "{request.language}",
        "code": "FULL_CODE_HERE",
        "tests": ["test_case_1", "test_case_2"],
        "dependencies": ["dep1", "dep2"],
        "confidence": 0.95,
        "explanation": "Brief explanation of implementation"
    }}
    
    IMPORTANT: 
    - The 'code' field must contain the COMPLETE source code, including imports.
    - Do not use markdown formatting like ```json or ```python in the JSON output if possible, but if you do, I will clean it.
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
        # Fallback for bad JSON
        return {
            "language": request.language,
            "code": response.text,  # Return raw text if JSON fails
            "tests": [],
            "dependencies": [],
            "confidence": 0.0,
            "explanation": "Failed to parse JSON output from model",
            "raw_output": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
