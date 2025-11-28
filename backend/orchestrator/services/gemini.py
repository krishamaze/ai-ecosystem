import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def call_gemini(prompt: str) -> str:
    """
    Call Gemini API and return raw text response.
    Raises exception on failure.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set")

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "maxOutputTokens": 2048
        }
    }

    response = httpx.post(
        f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
        json=payload,
        headers=headers,
        timeout=30.0
    )
    response.raise_for_status()

    data = response.json()
    # Extract text from Gemini response structure
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("No candidates in Gemini response")

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])
    if not parts:
        raise ValueError("No parts in Gemini response")

    return parts[0].get("text", "")

