"""
Single point of contact with OpenRouter. Nothing else in the codebase
should call requests.post directly -- keeps the API surface swappable
(e.g. if you ever want to switch models or providers).
"""

import requests

import config


def chat(messages, temperature=0.4):
    if not config.API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. See README.md for setup."
        )

    headers = {
        "Authorization": f"Bearer {config.API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config.MODEL,
        "messages": messages,
        "reasoning": {"enabled": True},
        "temperature": temperature,
    }

    r = requests.post(config.API_URL, headers=headers, json=payload, timeout=300)
    r.raise_for_status()
    data = r.json()

    choice = data["choices"][0]["message"]
    return {
        "content": choice.get("content") or "",
        "reasoning": choice.get("reasoning"),
    }
