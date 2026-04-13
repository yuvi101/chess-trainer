import os
import time
import logging


def call_llm(prompt):
    """
    Single entry point for all LLM calls.
    Switch models by changing LLM_PROVIDER in your .env file.
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        return _call_gemini(prompt)
    elif provider == "claude":
        return _call_claude(prompt)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _call_gemini(prompt):
    #import google.generativeai as genai
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    start = time.time()
    client = genai.Client()
    model = "gemini-3-flash-preview"
    response = client.models.generate_content(model=model, contents=prompt)
    latency_ms = int((time.time() - start) * 1000)

    content = response.text
    total_tokens = len(prompt + content) // 4  # rough estimate

    logging.info(f"Gemini response received — latency: {latency_ms}ms")

    return {
        "content": content,
        "tokens_used": total_tokens,
        "cost_usd": 0.0,  # free tier
        "latency_ms": latency_ms,
        "provider": "gemini",
        "model": "gemini-1.5-flash",
    }


def _call_claude(prompt):
    import requests

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    start = time.time()
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    response.raise_for_status()
    data = response.json()
    latency_ms = int((time.time() - start) * 1000)

    content = data["content"][0]["text"]
    input_tokens = data["usage"]["input_tokens"]
    output_tokens = data["usage"]["output_tokens"]
    total_tokens = input_tokens + output_tokens
    cost_usd = (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)

    logging.info(f"Claude response received — latency: {latency_ms}ms, cost: ${cost_usd:.4f}")

    return {
        "content": content,
        "tokens_used": total_tokens,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "provider": "claude",
        "model": "claude-sonnet-4-6",
    }