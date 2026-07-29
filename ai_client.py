"""
Wrapper around the OpenAI API for AI-generated content commands
(/voiceover and future ones like /cover).

Kept separate from cogs so the API client setup happens once, not per command.
"""

import os
from openai import AsyncOpenAI

_client = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file (locally) "
                "or Railway Variables (in production)."
            )
        _client = AsyncOpenAI(api_key=api_key)
    return _client


async def generate(system_prompt: str, user_message: str) -> str:
    """Single-turn chat completion. Returns the raw text response."""
    client = get_client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.9,  # higher temp helps satisfy "rotate phrasing, never reuse lines"
        max_tokens=900,
    )
    return response.choices[0].message.content
