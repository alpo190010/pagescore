"""Async OpenRouter API client with JSON extraction from AI responses."""

import json
import re

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def call_openrouter(
    prompt: str,
    api_key: str,
    model: str = "openai/gpt-5.4-nano",
    temperature: float = 0.3,
    max_tokens: int = 500,
    extract_array: bool = False,
) -> dict | list:
    """Call OpenRouter chat completions and extract JSON from the response.

    Args:
        prompt: The user prompt to send.
        api_key: OpenRouter API key (Bearer token).
        model: Model identifier.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.
        extract_array: If True, extract a JSON array instead of a JSON object.

    Returns:
        Parsed JSON dict (default) or list (when extract_array=True).

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
        ValueError: When no valid JSON is found in the AI response.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=body)
        response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"] or ""
    if not content:
        content = data["choices"][0]["message"].get("reasoning", "")

    pattern = r"\[[\s\S]*\]" if extract_array else r"\{[\s\S]*\}"
    match = re.search(pattern, content)
    if not match:
        raise ValueError("No JSON found in AI response")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError("No JSON found in AI response") from exc
