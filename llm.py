"""
llm.py — IBM watsonx.ai client wrapper for Street Vendor Growth Copilot.

Credentials are read exclusively from environment variables:
    WATSONX_API_KEY      — IBM Cloud API key
    WATSONX_PROJECT_ID   — watsonx.ai project ID
    WATSONX_URL          — service URL (defaults to Dallas endpoint)
    WATSONX_MODEL_ID     — Granite model ID (optional, has a default)

No credentials are ever hardcoded or printed.
"""

import os
from typing import Optional, Tuple

from dotenv import load_dotenv

load_dotenv()  # loads .env when running locally; safe no-op if absent

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_API_KEY: Optional[str] = os.environ.get("WATSONX_API_KEY")
_PROJECT_ID: Optional[str] = os.environ.get("WATSONX_PROJECT_ID")
_URL: str = os.environ.get(
    "WATSONX_URL", "https://us-south.ml.cloud.ibm.com"
)
_MODEL_ID: str = os.environ.get(
    "WATSONX_MODEL_ID", "ibm/granite-4-h-small"
)

# Lazily initialised — no network call at import time
_client = None


def is_configured() -> bool:
    """Return True only when all required credentials are present."""
    return bool(_API_KEY and _PROJECT_ID)


def configuration_message() -> str:
    """Human-readable hint about what is missing."""
    missing = []
    if not _API_KEY:
        missing.append("WATSONX_API_KEY")
    if not _PROJECT_ID:
        missing.append("WATSONX_PROJECT_ID")
    if missing:
        return (
            f"Missing environment variable(s): {', '.join(missing)}. "
            "Create a .env file (see .env.example) or set them in your shell."
        )
    return "All credentials are present."


def _get_client():
    """Return a cached ModelInference client; create it on first call."""
    global _client
    if _client is not None:
        return _client

    # Import here so the module can be imported without the SDK installed
    # (the app will show the config warning instead of crashing at import)
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
    except ImportError as exc:
        raise RuntimeError(
            "ibm_watsonx_ai package is not installed. "
            "Run: pip install ibm-watsonx-ai"
        ) from exc

    credentials = Credentials(url=_URL, api_key=_API_KEY)
    _client = ModelInference(
        model_id=_MODEL_ID,
        credentials=credentials,
        project_id=_PROJECT_ID,
    )
    return _client


def generate(
    prompt: str,
    max_tokens: int = 500,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Send *prompt* to IBM Granite via chat() and return (text, error).

    Returns:
        (generated_text, None)  on success.
        (None, error_message)   on failure or misconfiguration.

    No network request is made until this function is called explicitly.
    """
    if not is_configured():
        return None, configuration_message()

    try:
        from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

        client = _get_client()
        params = TextChatParameters(
            max_tokens=max_tokens,
            repetition_penalty=1.1,
        )
        messages = [{"role": "user", "content": prompt}]
        response = client.chat(messages=messages, params=params)

        # Extract assistant text from: response["choices"][0]["message"]["content"]
        choices = response.get("choices") if isinstance(response, dict) else None
        if choices and isinstance(choices, list) and len(choices) > 0:
            message = choices[0].get("message", {})
            text = message.get("content", "")
            if isinstance(text, str) and text.strip():
                return text.strip(), None

        return None, "watsonx.ai returned an empty or unrecognised response."

    except Exception as exc:  # noqa: BLE001
        # Return only the exception type — never the message body, which may
        # contain credential fragments, request headers, or token values.
        error_type = type(exc).__name__
        return None, f"watsonx.ai request failed ({error_type}). Check your credentials and project ID."
