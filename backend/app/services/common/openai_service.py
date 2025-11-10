from __future__ import annotations
import os
from openai import OpenAI

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=OPENAI_API_KEY)

# Default model - can be overridden per request
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def run_completion(prompt: str, model: str | None = None) -> str:
    """
    Run a simple text completion on the given prompt.
    """
    response = client.chat.completions.create(
        model=model or DEFAULT_OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def run_json_completion(prompt: str, model: str | None = None) -> dict:
    """
    Run a completion and parse response as JSON (useful for structured outputs).
    """
    response = run_completion(prompt, model)
    try:
        import json
        return json.loads(response)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON returned", "raw": response}
