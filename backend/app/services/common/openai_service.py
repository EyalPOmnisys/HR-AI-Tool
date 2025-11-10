from __future__ import annotations
import json
from openai import OpenAI
from app.core.config import settings


if not settings.OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in environment variables")

# Initialize the OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def run_completion(prompt: str, model: str | None = None) -> str:
    """
    Simple chat completion with OpenAI models.
    """
    model_name = model or settings.OPENAI_MODEL
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def run_json_completion(prompt: str, model: str | None = None) -> dict:
    """
    Run a completion and parse it as JSON (useful for structured extraction).
    """
    text = run_completion(prompt, model)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON returned", "raw": text}


def get_openai_embedding(text: str, model: str | None = None) -> list[float]:
    """
    Generate embeddings using OpenAI's embedding models.
    """
    model_name = model or settings.OPENAI_EMBEDDING_MODEL
    response = client.embeddings.create(
        model=model_name,
        input=text,
    )
    return response.data[0].embedding
